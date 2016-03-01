define(['app', 'service'], function (app) {

    'use strict';

    app.controller('queryListCtrl', ['filterConfigProduce'
        , 'configFactory', 'requestProxy', '$location', '$scope'
        , function(filterConfigProduce, configFactory, requestProxy
            ,$location, $scope, $sce){

        var formControls = {
                conf: {
                    keyName: 'postSourceUser' 
                },
                username: {
                    label: '用户名',
                    name: 'username',
                    require: true
                },
                password: {
                    label: '密码',
                    name: 'password',
                    require: true
                },
                limits: {
                    label: '限制条数',
                    name: 'limit',
                    require: true
                },
                names: null,
                pass: null,
                limit: 15,
            },
            paginationConf = {
                item: null,
                current: 0,
                total: null,
                getData: getData
            },
            requestConf = configFactory(['getSourceUser']),
            listData = {
                list: [],
                source: null
            },
            counts = 0;

        $scope.formControls = formControls;
        $scope.paginationConf = paginationConf;
        $scope.listData = listData;
        $scope.counts = counts;

        formControls.conf['success'] = function(data, status, headers){
            listData.list = data;
            paginationConf.item = data.length;
            paginationConf.total = data.length * headers('Page-total');
            requestConf.params = {limit: 15, sort: 'id desc', 
                username: String(formControls.names), 
                password: String(formControls.pass)};
            formControls.names = null;
            formControls.pass = null;
        }
        formControls.conf['error'] = function(data){
            listData.list = {};
            formControls.names = null;
            formControls.pass = null;
            paginationConf.total = null;
            paginationConf.item = null;
        }

        function getData(conf){
            if(conf){
                requestConf.params['offset'] = (conf - 1)*paginationConf.item;
            }
            requestProxy(requestConf)
                .success(function(data, status, headers){
                    if(!paginationConf.item){
                        paginationConf.item = data.length;
                        paginationConf.total = data.length * headers('Page-total');
                    }
                    listData.list = data;
                })
                .error(function(data){
                    listData.list = {};
                });
        }
    }]);
})
