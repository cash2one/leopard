define(['app', 'service'], function (app) {

    'use strict';

    app.controller('profileCtrl', ['requestProxy', 'messagePrompt'
        , '$scope'
        , function(requestProxy, messagePrompt, $scope){

        //set a config for edit profile
        var profileControls = {
                conf: {
                    keyName: 'changeProfile' //this is the config's name in 'config'
                },
                sex: {
                    label: '性别',
                    name: 'sex'
                },
                age: {
                    label: '年龄',
                    name: 'age',
                    pattern: '/^\\d+$/',
                    min: '1',
                    max: '120',
                    require: true
                },
                education: {
                    label: '学历',
                    name: 'education'
                },
                marital: {
                    label: '婚姻',
                    name: 'marital_status'
                },
                address: {
                    label: '户籍',
                    name: 'address',
                    require: true
                },
                models: {
                    sex: null,
                    age: null,
                    education: null,
                    marital: null,
                    address: null
                }
            };
        //set the callback function
        profileControls.conf['success'] = function(){
            messagePrompt.success('修改个人资料成功 !');
        }

        $scope.profileControls = profileControls;

        //get profile
        requestProxy({keyName: 'getProfile'})
            .success(function(data){
                var t = profileControls.models;
                t.sex = data.sex;
                t.age = data.age;
                t.education = data.education;
                t.marital = data.marital_status;
                t.address = data.address;
            });


        //set a config for edit phone
        var phoneControls = {
                conf: {
                    keyName: 'changePhone' //this is the config's name in 'config'
                },
                currentCode: {
                    label: '当前手机验证码',
                    name: 'current_phone_code',
                    keyName: 'changePhoneCode',
                    require: true
                },
                newPhone: {
                    label: '新手机号码',
                    name: 'phone',
                    pattern: '/^[1][1-9][\\d]{9}$/',
                    keyName: 'setPhoneCode',
                    isExist: 'checkRegisterExist',
                    require: true
                },
                newCode: {
                    label: '新手机验证码',
                    name: 'change_phone_code',
                    require: true
                },
                models: {
                    currentPhone: null,
                    newPhone: null,
                    code: null
                }
            };
        //set the callback function
        phoneControls.conf['success'] = function(){
            $scope.accountData.user.phone = phoneControls.models.newPhone;
            for(var i in phoneControls.models)
                phoneControls.models[i] = null;
            messagePrompt.success('修改绑定手机成功 !');
        }

        $scope.phoneControls = phoneControls;


        //set a config for edit email
        var mailControls = {
                conf: {
                    keyName: null //this is the config's name in 'config'
                },
                email: {
                    label: '邮箱地址',
                    name: '3',
                    pattern: '/\\w+([-+.]\\w+)*@\\w+([-.]\\w+)*\\.\\w+([-.]\\w+)*/',
                    require: true
                },
                phoneCode: {
                    label: '短信验证码',
                    name: 'phone_code',
                    keyName: 'setEmailCode',
                    require: true
                },
                models: {
                    email: null,
                    phoneCode: null
                },
                sendTxt: null,
                editFlag: false,
                tempMail: null
            }

        //get the status of email
        requestProxy({keyName: 'getEmail'})
            .success(function(data){
                if(data.authentication.fields){
                    mailControls.tempMail = data.authentication.fields[0].value;
                    mailControls.conf.keyName = 'changeEmail';
                    mailControls.sendTxt = '修改绑定邮箱';
                    mailControls.editFlag = !data.authentication.is_edit;
                }else{
                    mailControls.conf.keyName = 'setEmail';
                    mailControls.sendTxt = '立即绑定邮箱';
                }
            });
        //set the callback function
        mailControls.conf['success'] = function(){
            if(!mailControls.editFlag)
                mailControls.tempMail = mailControls.models.email;
            for(var i in mailControls.models)
                mailControls.models[i] = null;
            messagePrompt.success('请到新邮箱激活!');
        }

        $scope.mailControls = mailControls;

        //set a config for edit password
        var passwordControls = {
                conf: {
                    keyName: 'changePassword' //this is the config's name in 'config'
                },
                originalPass: {
                    label: '原始密码',
                    name: 'oldpassword',
                    require: true
                },
                newPass: {
                    label: '新密码',
                    name: 'newpassword',
                    pattern: '/^[a-z][a-z0-9]{7,31}$/i',
                    warning: '登录密码应由8-32位数字、英文组成且首位必须为字母',
                    require: true
                },
                rePass: {
                    label: '重复密码',
                    name: 'repassword',
                    seemAs: 'newpassword',
                    require: true
                },
                models: {
                    originalPass: null,
                    newPass: null,
                    rePass: null
                }
            };
        //set the callback function
        passwordControls.conf['success'] = function(){
            for(var i in passwordControls.models)
                passwordControls.models[i] = null;
            messagePrompt.success('修改登录密码成功 !');
        }

        $scope.passwordControls = passwordControls;

        //set a config for edit trade password
        var tradePassControls = {
                conf: {
                    keyName: ''  //this is the config's name in 'config'
                },
                newPass: {
                    label: '新交易密码',
                    name: '',
                    pattern: '/^[a-z][a-z0-9]{7,31}$/i',
                    warning: '登录密码应由8-32位数字、英文组成且首位必须为字母',
                    require: true
                },
                rePass: {
                    label: '重复交易密码',
                    name: 'repassword',
                    seemAs: '',
                    require: true
                },
                phoneCode: {
                    label: '短信验证码',
                    name: 'phone_code',
                    keyName: 'setTradeCode',
                    require: true
                },
                models: {
                    newPass: null,
                    rePass: null,
                    phoneCode: null
                }
            }
        //set the callback function
        tradePassControls.conf['success'] = function(){
            tradePassControls.tempMail = tradePassControls.models.email;
            for(var i in tradePassControls.models)
                tradePassControls.models[i] = null;
            messagePrompt.success('设置交易密码成功 !');
            $scope.accountData.user.trade_password_enable = true;
            tradePassControls.conf.keyName = 'changeTradePass';
            tradePassControls.newPass.name = 'newpassword';
            tradePassControls.rePass.seemAs = 'newpassword';
        }

        $scope.tradePassControls = tradePassControls;

        //set a config for edit realname
        var realnameControls = {
                conf: {
                    keyName: null,  //this is the config's name in 'config'
                },
                idNum: {
                    label: '身份证号码',
                    name: '1',
                    pattern: '/^[1-9]\\d{5}[1-9]\\d{3}((0\\d)|(1[0-2]))(([0|1|2]\\d)|3[0-1])[\\dX]{4}$/',
                    require: true
                },
                realname: {
                    label: '真实姓名',
                    pattern: '/[\\u4E00-\\u9FA5]/gm',
                    name: '2',
                    require: true
                },
                models: {
                    idNum: null,
                    realname: null
                },
                isCertify: false,
                tempId: null,
                editFlag: false,
                tempName: null
            }

        //get the status of realname
        requestProxy({keyName: 'getRealname'})
            .success(function(data){
                if(data.authentication.fields){
                    realnameControls.tempId = data.authentication.fields[0].value;
                    realnameControls.tempName = data.authentication.fields[1].value;
                    realnameControls.isCertify = data.authentication.status;
                    realnameControls.editFlag = data.authentication.is_edit;
                    if(!data.authentication.status)
                        realnameControls.conf.keyName = 'changeRealname';
                }else
                    realnameControls.conf.keyName = 'setRealname';
            });
        //set the callback function
        realnameControls.conf['success'] = function(data){
            realnameControls.tempId = realnameControls.models.idNum;
            realnameControls.tempName = realnameControls.models.realname;
            for(var i in realnameControls.models)
                realnameControls.models[i] = null;
            messagePrompt.success(data.message);
            realnameControls.editFlag = false;
        }
        realnameControls.conf['error'] = function(data){
            messagePrompt.error(data.message);
        }

        $scope.realnameControls = realnameControls;

        //wacher data of parent scope
        $scope.watcher = function(){
            var conf = $scope.accountData.user.trade_password_enable;
            if(conf === 'true' || conf === true || conf === false || conf === 'false')
                return conf + '';
            else
                return false;
        }

        var watcher = $scope.$watch('watcher()', function(data){
            if(data){
                var t = $scope.accountData.user.trade_password_enable?
                    'newpassword': 'password';
                tradePassControls.conf.keyName = $scope.accountData.user.trade_password_enable?
                    'changeTradePass': 'setTradePass';
                tradePassControls.newPass.name = t;
                tradePassControls.rePass.seemAs = t;

                //destroy watcher
                watcher();
            }
        })
    }]);

})
