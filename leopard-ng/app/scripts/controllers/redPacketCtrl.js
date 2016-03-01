define(['app', 'service'], function (app) {

    'use strict';

    app.controller('redPacketCtrl', ['requestProxy', 'messagePrompt'
        , 'configFactory', '$scope', '$route'
        , function(requestProxy, messagePrompt, configFactory, $scope, $route){
            var redPacketData = {
                    list: [],
                    unenable: {
                        is_available: false,
                        is_expiry: false,
                        is_use: false
                    },
                    unuse: {
                        is_available: true,
                        is_expiry: false,
                        is_use: false
                    },
                    used: {
                        is_available: true,
                        is_expiry: false,
                        is_use: true
                    },
                    overdue: {
                        is_available: false,
                        is_expiry: true,
                        is_use: false
                    }
                },
                usePacketConfig = configFactory(['useRedPacket']
                    , {params: {}});
            $scope.redPacketData = redPacketData;

            function getData(){
                requestProxy({keyName: 'getRedPacket'})
                    .success(function(data){
                        redPacketData.list = data;
                    });
            }
            getData();

            $scope.useRedPacket = function(id){
                usePacketConfig.params['packet_id'] = id;
                requestProxy(usePacketConfig)
                    .success(function(data){
                        getData();
                        messagePrompt.success(data.message);
                        $route.reload();
                    });
            }

            $scope.useAllPacket = function(){
                requestProxy({keyName: 'useAllPacket'})
                    .success(function(data){
                        getData();
                        messagePrompt.success(data.message);
                        $route.reload();
                    });
            }

            /* 兑换码红包 */
            var useCodeRedPacketConfig = configFactory(['useCodeRedPacket']
                    , {data: {}});
            $scope.useCodeRedPacket = function(){
                var codeValue = $scope.redPacketCodeValue;
                if(!codeValue){
                    messagePrompt.error("请输入兑换码！");
                }else{
                    useCodeRedPacketConfig.data['code'] = codeValue;
                    requestProxy(useCodeRedPacketConfig)
                        .success(function(data){
                            getData();
                            messagePrompt.success(data.message);
                            $route.reload();
                        });
                }
            }
    }]);
})
