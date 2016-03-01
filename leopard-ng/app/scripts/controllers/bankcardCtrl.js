define(['app', 'service', 'config'], function (app) {

    'use strict';

    app.controller('bankcardCtrl', ['requestProxy', 'messagePrompt'
        , 'configFactory', 'config', '$scope', '$location', '$modal', '$timeout'
        , function(requestProxy, messagePrompt, configFactory, config, $scope, $location
            , $modal, $timeout){
            var bankcardData = {
                    list: [],
                    maxNumber: config['platformConfig']['bankcardNumber']
                },
                formControls = {
                    conf: {
                        keyName: 'createBankcard' //this is the config's name in 'config'
                    },
                    bankNum: {
                        label: '银行卡号',
                        name: 'card',
                        pattern: '/^[0-9]{16,19}$/i',
                        require: true
                    },
                    bankName: {
                        label: '银行名称',
                        name: 'name',
                        require: true
                    },
                    bankOpen: {
                        label: '开户行',
                        name: 'branch',
                        require: true
                    },
                    models: {
                        bankNum: null,
                        bankName: null,
                        bankOpen: null
                    }
                },
                removeConf = null,
                bankcardModal = null,
                bankStyle = config['bankIconConfig'];
            //set the callback function
            formControls.conf['success'] = function(){
                $scope.resetModels();
                messagePrompt.success('添加银行卡成功 !');
                getData();
            }

            $scope.bankcardData = bankcardData;
            $scope.formControls = formControls;

            //get bankcard data
            function getData(){
                requestProxy({keyName: 'getBankcard'})
                    .success(function(data){
                        bankcardData.list = data;
                    });
            }
            getData();

            //set a function to get bank icons
            $scope.getBankClass = function(name){
                return bankStyle[name] || 'bank-default';
            }

            //check realname certify
            function check(){
                if(!$scope.accountData.user.username){
                    $timeout(check, 100);
                    return;
                }
                if(!$scope.accountData.user.realname){
                    messagePrompt.forbidden('请先进行实名认证');
                    $location.path('account/management/profile');
                }
            }
            check();

            //set a function to reset models
            $scope.resetModels = function(){
                for(var i in formControls.models)
                    formControls.models[i] = null;
            }
            //set a modal
            $scope.openModal = openModal;
            function openModal(id){
                removeConf = configFactory(['removeBankcard']
                    , {params: {'bankcard_id': id}});

                if(bankcardModal){
                    bankcardModal.close();
                }
                bankcardModal = $modal.open({
                    templateUrl: 'remove_bankcard_modal.html',
                    controller: ['$scope', '$modalInstance', 'conf', 'messagePrompt'
                , 'getData', bankcardModalIns],
                    resolve: {
                        conf: function() {
                            return removeConf;
                        },
                        getData: function(){
                            return getData;
                        }
                    }
                });
            }

            //set a modal controller
            var bankcardModalIns = function($scope, $modalInstance, conf
                , messagePrompt, getData){
                var removeInfo = {
                    tradePass: null
                }
                $scope.removeInfo = removeInfo;

                $scope.ok = function () {
                    if(!removeInfo.tradePass){
                        messagePrompt.forbidden('请先输入交易密码 !');
                        return
                    }
                    conf.params['trade_password'] = removeInfo.tradePass;
                    requestProxy(conf)
                        .success(function(){
                            messagePrompt.success('删除银行卡成功 !');
                            getData();
                        });
                    $modalInstance.close();
                };
                $scope.cancel = function () {
                    $modalInstance.dismiss();
                };
            };
    }]);
})