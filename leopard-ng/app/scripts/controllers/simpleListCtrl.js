define(['app', 'service'], function (app) {

    'use strict';

    app.controller('simpleListCtrl', ['filterConfigProduce'
        , 'configFactory', 'requestProxy', '$location', '$scope', '$sce'
        , function(filterConfigProduce, configFactory, requestProxy
            ,$location, $scope, $sce){
        var listType = $scope.paramView,
            filterConfig = {
                types: [{
                    title: '项目状态',
                    name: 'status',
                    values: {}
                }],
                getData: getData
            },
            requestConf = {},
            paginationConf = {
                item: null,
                current: 0,
                total: null,
                getData: getData
            },
            listData = {
                list: []
            };

        switch(listType){
            case 'deposit':
                filterConfig.types[0].values = filterConfigProduce('deposit');
                requestConf = configFactory(['getDeposit']);
                break;
            case 'log':
                filterConfig.types = [];
                requestConf = configFactory(['getLog']);
                break;
            case 'gift-point':
                requestConf = configFactory(['getGiftPoint']);
                filterConfig = null;

                requestProxy({keyName: 'getProductOrder'})
                .success(function(data){
                    $scope.orderData = data
                });
                break;
            case 'lending':
                filterConfig.types[0].values = filterConfigProduce('plan');
                requestConf = configFactory(['getPlans']);
                break;
            case 'apply':
                filterConfig.types[0].values = filterConfigProduce('apply');
                requestConf = configFactory(['getApply']);
                break;
            case 'student-apply':
                filterConfig.types[0].values = filterConfigProduce('student');
                requestConf = configFactory(['getStudentApply']);
                break;
            case 'student-repayment':
                filterConfig = null;
                requestConf = configFactory(['getStudentApply'],
                                            {params: {filter: {status:200}}});
                break;
            case 'finrepayment':
                filterConfig.types[0].values = filterConfigProduce('lend');
                requestConf = configFactory(['getFinRepayments']);
                break;
            default:
                $location.path('/account/dashboard');
        }
        if(!requestConf)
            return console.error('Not found configration for "' + listType
                + '" in config.js');

        $scope.filterConfig = filterConfig;
        $scope.paginationConf = paginationConf;
        $scope.listData = listData;
        requestConf.params = requestConf.params || {};

        function getData(conf){
            if(typeof(conf) == 'object'){
                paginationConf.item = null;
                requestConf.params['filter'] = conf;
            }
            else if(conf){
                requestConf.params['offset'] = (conf - 1)*paginationConf.item;
            }
            requestProxy(requestConf)
                .success(function(data, status, headers){
                    if(!paginationConf.item){
                        paginationConf.item = data.length;
                        paginationConf.total = data.length * headers('Page-total');
                    }
                    if(listType == 'log')
                        for(var i in data){
                            data[i].description = $sce.trustAsHtml(data[i].description);
                        }
                    listData.list = data;
                });
        }
        getData();
    }]);
})
