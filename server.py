import os,re,calendar
from datetime import datetime
from pathlib import Path
from uuid import getnode as get_mac
from flask import Flask, render_template, redirect, request, url_for, flash
from flask import current_app, session, send_from_directory
from flask_login import login_user, current_user, logout_user, login_required
from flask_mongoengine import MongoEngine
from mongoengine.queryset.visitor import Q
from mongoengine.connection import get_connection
from flask_ckeditor import CKEditor, CKEditorField, upload_success, upload_fail
from wtforms.validators import DataRequired, Length
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wordcloud import WordCloud
from bs4 import BeautifulSoup
#import matplotlib.pyplot as plt
'''
net start mongodb # win启动mongod服务
'''
app = Flask(__name__)
### 配置文件
app.config['SECRET_KEY'] = 'secret'
app.config['CKEDITOR_SERVE_LOCAL'] = True
app.config['CKEDITOR_FILE_UPLOADER'] = 'post_img_upload'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0 #用来强制刷新静态图片
MACHINE_MAC = get_mac()
if MACHINE_MAC == 20000: # getMAC
    # app.config["MONGO_URI"] = "mongodb://localhost:port/mlog"
    app.config['MONGODB_SETTINGS'] = {
        'db': 'mlog',
        'host': 'localhost',
        'port': 2222
    }
else:
    print("Wrong Machine!!")

### 实例化
db = MongoEngine(app)
ckeditor = CKEditor(app)

### 数据模型
class FormPost(FlaskForm):
    headline = StringField('标题', validators=[DataRequired()])
    summary = TextAreaField('摘要', validators=[Length(max=120)])
    tags = StringField('关键词')
    content = CKEditorField('内容', validators=[DataRequired()])
    submit = SubmitField('发布')

class FormSearch(FlaskForm):
    search_term = StringField("检索词" ,validators=[DataRequired()])
    submit = SubmitField('搜')

class DataWriter(db.Document): 
    name = db.StringField(max_length=32, required=True)
    email = db.EmailField(required=False)

class DataComment(db.EmbeddedDocument): # Embedded的文档需要在主文档之前定义
    created_at = db.DateTimeField(default=datetime.now, required=True)
    body = db.StringField(verbose_name="Comment", required=True)
    author = db.StringField(verbose_name="Name", max_length=255, required=True)

class DataPost(db.Document):
    created_at = db.DateTimeField(default=datetime.now, required=True)
    edited_at = db.DateTimeField(default=datetime.now, required=True)
    title = db.StringField(max_length=255, required=True)
    #author = db.ListField(db.EmbeddedDocumentField('DataWriter')) # 暂时不支持多作者
    author = db.ReferenceField(DataWriter)
    subtitle = db.StringField(max_length=2047, required=False)
    #slug = db.StringField(max_length=255, required=True) # 固定连接名
    keywords = db.ListField(db.StringField(max_length=255),required=False)
    body = db.StringField(required=True)
    body_plain = db.StringField()
    comments = db.ListField(db.EmbeddedDocumentField('DataComment'))
    view_count = db.IntField(default=0)
    #def get_absolute_url(self):
    #    return url_for('post', kwargs={"slug": self.slug})
    def __unicode__(self):
        return self.title
    meta = {
        'allow_inheritance': True,
        # 'indexes': [
        #     {
        #     'fields':['$title','$body_plain','$keywords'],
        #     'default_language':'chinese',
        #     'weights':{'title':5, 'body_plain':2,'keywords':4}
        #     }
        # ],
        'ordering': ['-created_at']
    }

### 使用函数
def get_calendar():
    calendar.setfirstweekday(firstweekday=6) #0是周一，6是周日
    cal = calendar.monthcalendar(datetime.now().year, datetime.now().month)
    if len(cal) != 6:
        cal.append([0 for _ in range(7)])
    return cal

def get_wordcloud(tags_freq):
    wc = WordCloud(background_color="#fdfdfe",font_path=os.path.join(current_app.root_path, 'static/post/wordcloud/GenWanMinTW-Regular.ttf'))
    wc.generate_from_frequencies(tags_freq)
    #print(tags_freq)
    wc.to_file(os.path.join(current_app.root_path, 'static/post/wordcloud/tags.png'))

def get_plaintext(html):
    soup = BeautifulSoup(html)
    for script in soup(["script", "style"]):
        script.extract()
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    return text

def get_posted_dates():
    pds = set()
    for p in DataPost.objects.all(): 
        if (p.created_at.year == datetime.now().year) and (p.created_at.month == datetime.now().month):
            pds.add(p.created_at.day)
    return pds

def expand_keywords(kwds):
    kwds_s =set(kwds)
    for kwd in kwds_s:
        if kwd == "集合":
            kwds_s.add("collection")
        if kwd == "collection":
            kwds_s.add("集合")
    return list(kwds_s)           

def cal_base_size(db):
    POST_IMAGE_FOLDER = os.path.join(current_app.root_path, 'static/post/uploaded/')
    root_directory = Path(POST_IMAGE_FOLDER)
    m_size = sum(f.stat().st_size for f in root_directory.glob('**/*') if f.is_file() )
    d_size = get_connection().get_database('mlog').eval('db.stats()')["storageSize"]
    def size2M(num):
        return num/(1024*1024)
    return size2M(d_size), size2M(m_size)

### 路径与视图
@app.route('/')
@app.route('/index')
def index():
    tags_freq = DataPost.objects.item_frequencies('keywords')
    get_wordcloud(tags_freq)
    return redirect(url_for("post_list"))

@app.route('/user') # 最开始需要用这个方法作为注册和登录
def user():
    post_author = DataWriter(name="highwind")
    post_author.save()
    return redirect(url_for("post_list"))

@app.route('/post/show/list')
def post_list():
    formS = FormSearch()
    page = request.args.get('page', 1, type=int)
    posts = DataPost.objects.order_by('-created_at').paginate(page=page, per_page=3) #每次只查询部分数据库内容，减少每次负荷 DataPost.objects.all()
    return render_template('post_show_mul.html',
            posts=posts, 
            posts_count=DataPost.objects.count(),
            calendar=get_calendar(), 
            today=datetime.now(),
            posted_date=get_posted_dates(),
            forms=formS,
            database_size=cal_base_size(DataPost)[0],
            mediabase_size=cal_base_size(DataPost)[1]
            )

@app.route('/post/show/track')
def post_timeline():
    formS = FormSearch()
    page = request.args.get('page', 1, type=int)
    posts = DataPost.objects.order_by('created_at').paginate(page=page, per_page=20) # 如果是 .all()则注意后面就不用.items去调用了
    return render_template('post_show_timeline.html',
            posts=posts,
            posts_count=DataPost.objects.count(),
            calendar=get_calendar(), 
            today=datetime.now(),
            posted_date=get_posted_dates(),
            forms=formS,
            database_size=cal_base_size(DataPost)[0],
            mediabase_size=cal_base_size(DataPost)[1]
            )

@app.route('/post/show/list/tag/<string:post_tag>')
def post_list_by_tag(post_tag):
    formS = FormSearch() 
    page = request.args.get('page', 1, type=int)
    posts = DataPost.objects(keywords=post_tag).order_by('-created_at').paginate(page=page, per_page=3) #每次只查询部分数据库内容，减少每次负荷 DataPost.objects.all()
    return render_template('post_show_mul_by_tag.html',
            posts=posts, 
            posts_count=DataPost.objects.count(),
            calendar=get_calendar(), 
            today=datetime.now(),
            posted_date=get_posted_dates(),
            forms=formS,
            database_size=cal_base_size(DataPost)[0],
            mediabase_size=cal_base_size(DataPost)[1]
            )

@app.route('/post/show/list/date/<int:post_day>')
def post_list_by_date(post_day):
    formS = FormSearch() 
    page = request.args.get('page', 1, type=int)
    date_start = datetime(datetime.now().year, datetime.now().month, post_day, 0,0,0,0)
    date_end = datetime(datetime.now().year, datetime.now().month, post_day, 23,59,59,999)
    posts = DataPost.objects((Q(created_at__gte=date_start) & Q(created_at__lte=date_end)))\
        .order_by('-created_at').paginate(page=page, per_page=3) #每次只查询部分数据库内容，减少每次负荷 DataPost.objects.all()
    return render_template('post_show_mul.html',
            posts=posts, 
            posts_count=DataPost.objects.count(),
            calendar=get_calendar(), 
            today=datetime.now(),
            posted_date=get_posted_dates(),
            forms=formS,
            database_size=cal_base_size(DataPost)[0],
            mediabase_size=cal_base_size(DataPost)[1]
            )

@app.route('/post/show/<string:post_id>')
def post_show(post_id):
    formS = FormSearch()
    post_now=DataPost.objects.get_or_404(id=post_id)
    post_now.view_count += 1
    post_now.save()
    post_pre = DataPost.objects.filter(created_at__lt=post_now.created_at).order_by('-created_at').first()
    post_nex = DataPost.objects.filter(created_at__gt=post_now.created_at).order_by('created_at').first()
    return render_template('post_show_one.html',post=post_now, post_prev=post_pre, post_next=post_nex, forms=formS)
    
@app.route('/post/edit/new', methods=['GET','POST'])
def post_new():
    formS = FormSearch()  
    form = FormPost()
    #if request.method == 'POST':
        #data = request.form.get('ckeditor')  # <--
    post = DataPost(title="",body="")    
    if form.validate_on_submit():
        post.title = form.headline.data
        post.subtitle = form.summary.data
        # post.keywords = expand_keywords(re.split(",|，|;|；| ",form.tags.data)) # 以后可以对某些关键词进行自动扩展
        post.keywords = re.split(",|，|;|；| ",form.tags.data)
        post.body = form.content.data
        post.body_plain = get_plaintext(form.content.data)
        post.edited_at = datetime.now()
        post.author = DataWriter.objects(name='highwind').first()
        post.save()
        flash(f'文章 {form.headline.data} 已更新', 'success')
        return redirect(url_for('post_show', post_id=post.id))
    elif request.method == 'GET':
        form.headline.data = post.title
        form.summary.data = post.subtitle
        form.tags.data = "；".join(post.keywords)
        form.content.data = post.body
    else:
        pass #?? 还有那些情况呢？
    return render_template('post_edit.html', form=form, forms=formS) 

@app.route('/post/edit/<string:post_id>', methods=['GET','POST'])
def post_edit(post_id):
    post = DataPost.objects.get_or_404(id=post_id) # 就不是_id，而且id也不是python保留字
    # if post.author != current_user:
    #     abort(403)
    formS = FormSearch()
    form = FormPost()
    if form.validate_on_submit():
        post.title = form.headline.data
        post.subtitle = form.summary.data
        post.keywords = re.split(",|，|;|；",form.tags.data)
        post.body = form.content.data
        post.body_plain = get_plaintext(form.content.data)
        post.edited_at = datetime.now()
        #post.author.append(post_author) #暂时不支持多作者编辑
        post.author = DataWriter.objects(name='highwind').first()
        post.save()
        flash(f'文章 {form.headline.data} 已更新', 'success')
        return redirect(url_for('post_show', post_id=post.id))
    elif request.method == 'GET':
        form.headline.data = post.title
        form.summary.data = post.subtitle
        form.tags.data = "；".join(post.keywords)
        form.content.data = post.body
    else:
        pass #?? 还有那些情况呢？
    #formNavLogin=generate_navbar_login_form()
    return render_template('post_edit.html', form=form, forms=formS) 

@app.route('/post/edit/delete/<string:post_id>', methods=['POST'])
#@login_required
def post_delete(post_id):
    post = DataPost.objects.get_or_404(id=post_id)
    #if post.author != current_user:
    #    abort(403)
    print(post.id)
    post.delete()
    flash(f'文章 {post.title} 已删除', 'success')
    return redirect(url_for('post_list'))

@app.route('/post/files/<path:filename>')
def upload_file(filename):
    POST_IMAGE_FOLDER = os.path.join(current_app.root_path, 'static/post/uploaded/')
    return send_from_directory(POST_IMAGE_FOLDER, filename)

@app.route('/post/files/upload', methods=['POST'])
def post_img_upload():
    allowed_ext = ['jpg', 'jpeg', 'png', 'bmp', 'gif']
    POST_IMAGE_FOLDER = os.path.join(current_app.root_path, 'static/post/uploaded/')
    f = request.files.get('upload') # 注意 传入request.files.get()的键必须为'upload'， 这是CKEditor定义的上传字段name值。 
    f_extension = f.filename.split('.')[1].lower()
    if f_extension not in allowed_ext:
        return upload_fail(message=f'只允许以下格式图片（{str(allowed_ext)}）')
    f.save(os.path.join(POST_IMAGE_FOLDER, f.filename))
    f_url = url_for('upload_file', filename=f.filename)
    return upload_success(url = f_url)

@app.route('/post/search/', methods=['POST'])
def post_search():
    # if post.author != current_user:
    #     abort(403)
    formS = FormSearch()
    if formS.validate_on_submit():
        swd=formS.search_term.data
        page = request.args.get('page', 1, type=int)
        posts = DataPost.objects(body_plain__icontains=swd).order_by('-created_at').paginate(page=page, per_page=3)
        # posts = DataPost.objects.search_text(swd).order_by('$text_score').paginate(page=page, per_page=3) # 目前还不支持中文
    return render_template('post_show_mul.html',
            posts=posts, 
            posts_count=DataPost.objects.count(),
            calendar=get_calendar(), 
            today=datetime.now(),
            posted_date=get_posted_dates(),
            forms=formS,
            database_size=cal_base_size(DataPost)[0],
            mediabase_size=cal_base_size(DataPost)[1]
            )

@app.route('/sci/')
def science():
    formS = FormSearch() 
    return render_template('science.html',
            calendar=get_calendar(), 
            today=datetime.now(),
            posted_date=get_posted_dates(),
            forms=formS
            )

@app.errorhandler(404)
def error_404(error):
    formS = FormSearch() 
    return render_template('error_404.html', calendar=get_calendar(), today=datetime.now(), forms=formS), 404

### 运行服务
if __name__ == "__main__":
    if MACHINE_MAC == 20000: 
        app.run(debug=True, host='127.0.0.1', port='88')
    else:
        print("Wrong Machine???")