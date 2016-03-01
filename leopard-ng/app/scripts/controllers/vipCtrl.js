define(['app', 'service'], function (app) {

    'use strict';

    app.controller('vipCtrl', ['financeTools', 'requestProxy', 'messagePrompt'
        , '$scope', '$modal', '$location'
        , function(financeTools, requestProxy, messagePrompt, $scope, $modal, $location){

        var vipData = {
                vipFee: {},
                services: [],
                serviceId: null
            },
            investModal = null;

        $scope.vipData = vipData;

        //get the infomation of vip
        requestProxy({keyName: 'getVipInfo'})
            .success(function(data){
                vipData.vipFee = data;
            });

        //get the customer services
        requestProxy({keyName: 'getCustomerService'})
            .success(function(data){
                vipData.services = data;
                vipData.serviceId = data[0].id;
            });

        //set a function to change customer service
        $scope.selectVip = function(id){
            vipData.serviceId = id;
        }

        //set a function to updata data of user
        function updateUser(){
            requestProxy({keyName: 'getUser'})
                .success(function(data){
                    $scope.accountData.user = data;
                });
        }

        //set a modal
        $scope.charge = function (){
            if($scope.accountData.user.available_amount < vipData.vipFee.vip_commssion){
                messagePrompt.forbidden('余额不足, 请先充值 !');
                $location.path('/account/deposit');
                return;
            }
            if(investModal){
                investModal.close();
            }
            investModal = $modal.open({
                templateUrl: 'charge_vip_modal.html',
                controller: ['$scope', '$modalInstance', 'serviceId', 'user', 'vipInfo'
                , 'updateUser', 'requestProxy', 'configFactory', vipModalIns],
                resolve: {
                    serviceId: function(){
                        return vipData.serviceId;
                    },
                    user: function(){
                        return $scope.accountData.user;
                    },
                    vipInfo: function(){
                        return vipData.vipFee;
                    },
                    updateUser: function(){
                        return updateUser;
                    }
                }
            });
        }
        //set a modal controller
        var vipModalIns = function($scope, $modalInstance, serviceId, user, vipInfo
            , updateUser, requestProxy, configFactory){
            $scope.vipInfo = vipInfo;
            $scope.ok = function () {
                var conf = configFactory(['setVip'], {params: {charge: true}});
                requestProxy(conf)
                    .success(function(data){
                        if(!user.is_vip){
                            conf = configFactory(['setCustomerService'], {data: {id: serviceId}});
                            requestProxy(conf)
                                .success(function(data){
                                    messagePrompt.success(data.message);
                                    updateUser();
                                });
                        }else{
                            messagePrompt.success(data.message);
                            updateUser();
                        }
                    });
                $modalInstance.close();
            };
            $scope.cancel = function () {
                $modalInstance.dismiss();
            };
        };
    }]);

})