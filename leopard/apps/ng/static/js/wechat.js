var hostName = 'http://www.zhongbaodai.com/';

var allInputs = $('input[type=text], input[type=password]'),
    confs = [
        {
            label: '用户名',
            name: 'username',
            pattern: '/^[a-zA-Z0-9\\u4E00-\\u9FA5]{3,32}$/',
            tooltip: '用户名应由3-32位数字、英文或中文组成 !'
        },
        {
            label: '密码',
            name: 'password',
            pattern: '/^[a-z][a-z0-9]{7,31}$/i',
            tooltip: '登录密码应由8-32位数字、英文组成且首位必须为字母'
        }, 
        {
            label: '确认密码',
        }, 
        {
            label: '手机号码',
            name: 'phone',
            pattern: '/^[1][1-9][\\d]{9}$/'
        }, 
        {
            label: '验证码',
            name: 'phone_code'
        }
    ];

function register(){
    var data = {};

    for(var i = 0;i<allInputs.size();i++){
        var val = $.trim(allInputs.eq(i).val());
        
        if(!checkValByConf(val, i)){
            return;
        }

        // render form data
        if(confs[i].name) {
            data[confs[i].name] = val;
        }
    }

    if(allInputs.eq(1).val() != allInputs.eq(2).val()){
        return tooltip('两次密码不一致 !');
    }

    $.ajax({
        url: hostName + 'service/auth/user',
        type: 'POST',
        dataType: 'json',
        headers: {'X-CSRFToken': $.cookie('_csrf_token')},
        data: data,
        success:function(data) {
            window.location.href = hostName +'#!/?success=注册成功!'
        },
        error: function(data, status) {
            tooltip(data.responseJSON.message);
        }
    });
}

function sendSMS(){
    if(!checkValByConf(allInputs.eq(3).val(), 3))
        return;

    timeoutBtn();

    $.get(hostName + 'service/auth/phone_code/register', {
        phone: allInputs.eq(3).val()
    }, function(data){
        tooltip(data.message);
    }, function(data){
        tooltip(data.message);
    })
}

function timeoutBtn(){
    var btn = $('#sendBtn');

    btn.attr('disabled', 'disabled');
    setBtnTxt(60);

    function setBtnTxt(i){
        if(i <= 0){
            btn.html('发送验证码');
            btn.removeAttr('disabled');
            return;
        }

        btn.html('请等待' + i + '秒');
        setTimeout(function(){
            setBtnTxt(--i);
        }, 1000);
    }
}

function checkValByConf(val, index){
    if(val == '' || val == null || val == undefined){
        tooltip(confs[index].label + '不能为空 !');
        return false;
    }

    // check regExp
    if(confs[index].pattern){
        var t = confs[index].pattern.split('/'),
            reg = new RegExp(t[1], t[t.length - 1]);

        if(!reg.test(val)){
            tooltip(confs[index].tooltip || confs[index].label + '不符合规范 !');
            return false;
        }
    }
    return true;
}

function tooltip(txt, callback){
    $('._tooltip').remove();

    var elem = $('<div></div>');

    elem.css({
        position: 'fixed',
        top: '45%',
        left: '50%',
        marginLeft: '-35%',
        width: '70%',
        padding: '10px 10px',
        color: '#fff',
        textAlign: 'center',
        lineHeight: '20px',
        fontSize: '14px',
        backgroundColor: '#000',
        boxSizing: 'border-box',
        opacity: 0.8,
        borderRadius: 5
    });

    elem.html(txt);

    $('body').append(elem);

    setTimeout(function(){
        elem.remove();
        if(callback)
            callback();
    }, 1500);
}