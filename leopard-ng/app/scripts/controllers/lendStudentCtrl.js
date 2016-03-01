define(['app', 'service'], function (app) {

    'use strict';

    app.controller('lendStudentCtrl', ['configFactory', 'requestProxy', 'messagePrompt', '$scope', '$modal'
        , function(configFactory, requestProxy, messagePrompt, $scope, $modal){

        var lendApplyControls = {
            conf: {
                keyName: 'lendStudentApply'
            },
            amount: {
                label: '借款金额',
                name: 'amount',
                pattern: '/^\\d+000$/',
                min: 1000,
                max: 999999999,
                warning: '借款金额必须为1000的倍数',
                require: true
            },
            periods: {
                label: '期数',
                name: 'periods',
                pattern: '/^\\d+$/',
                min: 1,
                require: true
            },
            loanUseFor: {
                label: '贷款用途',
                name: 'loan_use_for',
                require: true
            },
            realname: {
                label: '姓名',
                name: 'realname',
                require: true
            },
            schoolName: {
                label: '学校名称',
                name: 'school_name',
                require: true
            },
            eduPassword: {
                label: '学信网密码',
                name: 'edu_passwd',
                require: true
            },
            idcard: {
                label: '身份证号码',
                name: 'idcard',
                pattern: '/^[1-9]\\d{5}[1-9]\\d{3}((0\\d)|(1[0-2]))(([0|1|2]\\d)|3[0-1])[\\dX]{4}$/',
                require: true
            },
            studentCode: {
                label: '学号',
                name: 'student_code',
                require: true
            },
            eduSystem: {
                label: '学制',
                name: 'edu_system',
                require: true
            },
            address: {
                label: '家庭地址',
                name: 'address',
                require: true
            },
            schoolAddr: {
                label: '学校地址',
                name: 'school_address',
                require: true
            },
            mobile: {
                label: '手机号码',
                name: 'mobile',
                pattern: '/^[1][1-9][\\d]{9}$/',
                require: true
            },
            wechat: {
                label: '微信号',
                name: 'wechat',
                require: true
            },
            compositeRank: {
                label: '综合成绩排名',
                name: 'composite_rank',
                pattern: '/^\\d+$/',
                require: true
            },
            tel: {
                label: '家庭固话',
                name: 'tel',
                require: true
            },
            qq: {
                label: 'QQ号',
                name: 'qq',
                require: true
            },
            classSize: {
                label: '班级人数',
                name: 'class_size',
                pattern: '/^\\d+$/',
                require: true
            },
            dad: {
                label: '父亲姓名',
                name: 'dad',
                require: true
            },
            dadUnit: {
                label: '父亲单位名称',
                name: 'dad_unit',
                require: true
            },
            dadUnitPhone: {
                label: '父亲单位固话',
                name: 'dad_unit_phone',
                require: true
            },
            dadUnitAddr: {
                label: '父亲单位地址',
                name: 'dad_unit_address',
                require: true
            },
            dadPhone: {
                label: '父亲手机号码',
                name: 'dad_phone',
                pattern: '/^[1][1-9][\\d]{9}$/',
                require: true
            },
            mum: {
                label: '母亲姓名',
                name: 'mum',
                require: true
            },
            mumUnit: {
                label: '母亲单位名称',
                name: 'mum_unit',
                require: true
            },
            mumUnitPhone: {
                label: '母亲单位固话',
                name: 'mum_unit_phone',
                require: true
            },
            mumUnitAddr: {
                label: '母亲单位地址',
                name: 'mum_unit_address',
                require: true
            },
            mumPhone: {
                label: '母亲手机号码',
                name: 'mum_phone',
                pattern: '/^[1][1-9][\\d]{9}$/',
                require: true
            },
            roommate: {
                label: '大学舍友姓名',
                name: 'roommate',
                require: true
            },
            roommatePhone: {
                label: '大学舍友手机号码',
                name: 'roommate_phone',
                pattern: '/^[1][1-9][\\d]{9}$/',
                require: true
            },
            coacher: {
                label: '大学辅导员姓名',
                name: 'coacher',
                require: true
            },
            coacherPhone: {
                label: '大学辅导员手机号码',
                name: 'coacher_phone',
                pattern: '/^[1][1-9][\\d]{9}$/',
                require: true
            },
            schoolmate: {
                label: '大学同学姓名',
                name: 'schoolmate',
                require: true
            },
            schoolmatePhone: {
                label: '大学同学手机号码',
                name: 'schoolmate_phone',
                pattern: '/^[1][1-9][\\d]{9}$/',
                require: true
            },
            pluses: {
                label: '个人荣誉介绍',
                name: 'pluses',
                require: true
            },
            agreement: {
                label: '申请合约',
                name: 'agreement',
                pattern: '/true/',
                warning: '请先同意申请表申请合约',
                require: true
            },
            models: {
                periods: 6,
                eduSystem: '四年制',
                agreement: 1
            }
        },
        agreementModal = null,
        addrMapping = {
            address: ['province', 'city', 'area', 'street', 'alley'],
            schoolAddr: ['province', 'city', 'university', 'campus', 'building', 'dorm']
        };

        lendApplyControls.conf['success'] = function(data){
            messagePrompt.success(data.message);
            lendApplyControls.models = {
                periods: 6,
                eduSystem: '四年制',
                agreement: 1
            }
        }

        $scope.lendApplyControls = lendApplyControls;

        $scope.showAgreement = function(){

            if(agreementModal){
                agreementModal.close();
            }
            agreementModal = $modal.open({
                templateUrl: 'agreement.html',
                controller: ['$scope', '$modalInstance', agreementModalIns]
            });
        }
        //set a modal controller
        var agreementModalIns = function($scope, $modalInstance){
            $scope.close = function () {
                $modalInstance.dismiss();
            };
        };

        // set a function to splice address
        $scope.spliceAddr = function(key){
            var str = '',
                mapping = addrMapping[key];

            for(var i = 0;i<mapping.length;i++){
                str += lendApplyControls.tempModels[key][mapping[i]] || '';
            }

            lendApplyControls.models[key] = str;
        }

        $scope.studentBanner = null;
        var getStudentApplyBanner = configFactory(['getStudentApplyBanner']);
        requestProxy(getStudentApplyBanner)
            .success(function(data){
                $scope.studentBanner = data;
            });

        $scope.promptUser = function () {
            if(!$scope.CURRENT_USER_ID){
                messagePrompt.forbidden('请先登录！');
            }
        }
    }]);

})
