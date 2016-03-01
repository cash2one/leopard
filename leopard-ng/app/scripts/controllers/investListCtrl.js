define(['app', 'service'], function (app) {

    'use strict';

    app.controller('investListCtrl', ['configFactory', 'requestProxy'
        , 'financeTools', '$scope', '$location'
        , function(configFactory, requestProxy, financeTools, $scope, $location){
        var requestConf = null,
            paginationConf = {
                item: null,
                current: 0,
                total: null,
                getData: getData
            },
            listData = {
                list: [],
                isInvest: $location.path()=='/invest' || $location.path()=='/invest/student',
                isStudent: $location.path()=='/invest/student'
            };

        $scope.paginationConf = paginationConf;
        $scope.listData = listData;

        requestConf = configFactory([listData.isInvest?
            listData.isStudent?'getStudentProjectList': 'getProjectList': 'getAssignmentList']);

        requestConf.params = {limit: 10, sort: 'status asc|id desc'};

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
                    //set some attributes when the project was assignment
                    if(!listData.isInvest)
                        for(var i in data){
                            data[i].name = data[i].project_info.name;
                            data[i].discount = data[i].discount;
                            data[i].rate = data[i].project_info.rate;
                            data[i].guarantee_name = data[i].project_info.guarantee;
                            data[i].guarantee_id = data[i].project_info.guarantee_id;
                            data[i].repaymentmethod = data[i].project_info.repaymentmethod;
                            data[i].invest_award = data[i].project_info.invest_award
                        }
                    for(var i in data){
                        data[i].invest_award = data[i].invest_award * 1.0 * 100
                    }
                    listData.list = data;
                });
        }
        getData();

        $scope.getInterest = function(rate, periods, type, reward){
            return financeTools.getInterest(rate, 100, periods, type, reward);
        }
    }]);
})
