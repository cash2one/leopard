define(['app', 'config', 'service'], function (app) {

    'use strict';

    app.controller('accountCtrl', ['$filter', '$location', '$routeParams', '$scope', 'config'
        , 'requestProxy', 'configFactory'
        , function ($filter, $location, $routeParams, $scope, config, requestProxy, configFactory) {
        var accountConfig = config['accountUrl'],
            urlCategory = null,
            paramCategory = $routeParams['category'],
            paramView = $routeParams['view'];

        $scope.paramView = paramView;
        //find the category from account urls
        for(var i=0;i<accountConfig.length;i++)
            if(accountConfig[i].id == paramCategory)
                urlCategory = accountConfig[i];

        //get template by routeparams
        if(!paramCategory)
            $scope.accountTemplate = accountConfig[0].templateUrl;
        else if(!urlCategory){
            return $location.path('/404');
        }else if(urlCategory.templateUrl)
            $scope.accountTemplate = urlCategory.templateUrl;
        else if(paramView){
            //find template from category's children
            for(var i=0;i<urlCategory.links.length;i++)
                if(urlCategory.links[i].id == paramView)
                    $scope.accountTemplate = urlCategory.links[i].templateUrl;

            if(!$scope.accountTemplate){
                return $location.path('/404');
            }
        }else{
            return $location.path('/404');
        }

        //set navbar of left from configs
        $scope.leftNavbarUrl = config['accountUrl'];

        //get user's profile
        var accountData = {
            user: {},
            recentMorris: {
                data: {},
                type: 'bar',
                xkeys: ['money', 'interest'],
                labels: ['金额', '利息']
            }
        }
        $scope.accountData = accountData;
        requestProxy({keyName: 'getUser'})
            .success(function(data){
                accountData.user = data;
                accountData.user.friend_invitation_url = $location.protocol() + '://' + $location.host() + '/#!/register?invited=' + accountData.user.friend_invitation;
            });

        //get recent collections
        var recentConf = configFactory(['getPlans']
            , {params: {sort: 'added_at asc', limit: 5}});

        requestProxy(recentConf)
            .success(function(list){
                var temp = [];
                for(var i=0;i<list.length;i++){
                    var recent = {
                        'y': $filter('date')(list[i].plan_time, 'yyyy-MM-dd HH:mm'),
                        'money': list[i].amount,
                        'interest': list[i].interest
                    }
                    temp.push(recent);
                }
                accountData.recentMorris.data = temp;
            });
    }]);

});
