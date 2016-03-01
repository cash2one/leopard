define(['app', 'service', 'config'], function (app) {

    'use strict';

    app.controller('messageCtrl', ['configFactory', 'requestProxy', 'messagePrompt', '$scope'
        , '$routeParams', '$location', '$sce', '$modal'
        , function(configFactory, requestProxy, messagePrompt, $scope, $routeParams, $location
            , $sce, $modal){
        var messageData = {
                list: []
            },
            guaranteeId = $routeParams['id'],
            messageConf = {},
            readConf = {},
            removeConf = {},
            paginationConf = {
                item: null,
                current: 0,
                total: null,
                getData: getData
            },
            investModal = null;
        $scope.paginationConf = paginationConf;
        $scope.messageData = messageData;

        //produce message config
        messageConf = configFactory(['getMessages'], {params: {}});

        //set a function to get data
        function getData(conf){
            if(conf){
                messageConf.params['offset'] = (conf - 1)*paginationConf.item;
            }
            requestProxy(messageConf)
                .success(function(data, status, headers){
                    if(!paginationConf.item){
                        paginationConf.item = data.length;
                        paginationConf.total = data.length * headers('Page-total');
                    }
                    messageData.list = data;
                });
        }
        getData();
        //set a function to delete message 
        $scope.readMessage = function(message){
            if(message.is_read)
                return;
            readConf = configFactory(['readMessage'], {params: {message_id: message.id}});
            requestProxy(readConf)
                .success(function(){
                    message.is_read = true;
                });
        }

        //set a modal
        $scope.removeMessage = function (id){
            if(investModal){
                investModal.close();
            }
            investModal = $modal.open({
                templateUrl: 'remove_message_modal.html',
                controller: ['$scope', '$modalInstance', 'remove', removeModalIns],
                resolve: {
                    remove: function(){
                        return function(){
                            removeConf = configFactory(['removeMessage']
                                , {params: {message_id: id}});
                            requestProxy(removeConf)
                                .success(function(){
                                    getData();
                                    messagePrompt.success('删除消息成功 !');
                                });
                        }
                    }
                }
            });
        }
        //set a modal controller
        var removeModalIns = function($scope, $modalInstance, remove){
            $scope.ok = function(){
                remove();
                $modalInstance.close();
            }
            $scope.cancel = function () {
                $modalInstance.dismiss();
            };
        };
    }]);
})