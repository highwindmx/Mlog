$(document).ready(function(){
    $('#button-nim-rd').click(function(){
        $('.nim-win-loss').hide();
        $.getJSON('/game_nim_gen_list', {
                now: new Date().getTime() // 一种刷新缓存的技巧
            },
            function(data) {
                $("#nim-layout").html(data.layout); //这样就可以避免在这里插入jinja2语句块的尴尬
                // console.log(data)
        });
    });
    $('#nim-layout').on('click', '.nim-stone-btn',function(){ //注意这里'.nim-layout'必须是静态的，而'.nim-stone-btn'可以是动态的
        var stone_pos = $(this).val();
        // console.log(stone_pos);
        $.getJSON('/game_nim_gen_list', {
            stone: stone_pos,
            now: new Date().getTime() // 一种刷新缓存的技巧
            },
            function(data) {
                // console.log(data);
                $('#nim-layout').html(data.layout); //这样就可以避免在这里插入jinja2语句块的尴尬
                $('#nim-number').text(data.nim_num);
                if (data.nim_w_o_l){
                    $('.nim-win-loss').show();
                } else {
                    $("#nim-player1").toggle();
                    $("#nim-player2").toggle();
                }
            }
        );
        // $("#nim-player1").toggle();
        // $("#nim-player2").toggle();
        // $.ajax({
        //     type: 'GET',
        //     url: "/game_nim_gen_list",
        //     data: JSON.stringify(stone_pos),
        //     dataType: 'json', // 注意：这里是指希望服务端返回json格式的数据
        //     contentType:'application/json; charset=utf-8',
        //     success: function(data) { 
        //         $("#nim-layout").html(data.layout);
        //         $("#nim-player1").toggle();
        //         $("#nim-player2").toggle();
        //     },
        //     error: function(xhr, type) {
        //         console.log("notcool");
        //     }
        // });
    });
    $('#button-24-sw').on('click', function(){
        $('.cards-24-exp').show();
    });
    $('#button-24-rd').click(function(){
        $('.cards-24-exp').hide();
        $.getJSON('/game_24_point', {
            now: new Date().getTime() // 一种刷新缓存的技巧
            },
            function(data) {
                $('.cards-24-list').html(data.cards_layout);
                $('.cards-24-exp').html(data.av_exp_layout);
            }
        );
    });
});
