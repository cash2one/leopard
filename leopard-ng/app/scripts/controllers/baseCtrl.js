define(['app', 'config', 'service'], function (app) {

    'use strict';

    app.controller('baseCtrl', ['messagePrompt', 'checkPermission', 'requestProxy'
        , 'config', '$scope', '$rootScope', '$location'
        , function (messagePrompt, checkPermission, requestProxy, config, $scope
            , $rootScope, $location) {
        //read config from 'config'
        $scope.navbarUrl = config['navbar'];
        $scope.friendUrl = config['friendLinks'];
        $scope.bottomNavbar = config['bottomNavbar'];
        $scope.platformConfig = config['platformConfig'];
        $scope.bannerConfig = config['bannerConfig'].list;
        $scope.partners = config['partners'];

        //check login
        checkPermission(true).then(
            function(){
                requestProxy({keyName: 'getUser'})
                    .success(function(data){
                        $rootScope.CURRENT_USER_ID = data.id;
                        $rootScope.CURRENT_USER_NAME = data.username;
                    })
            }
        )

        //create a function for logout
        $scope.logout = function(){
            requestProxy({keyName: 'logout'})
                .success(function(){
                    messagePrompt.success('安全退出成功 !');
                    $rootScope.CURRENT_USER_ID = null;
                    $rootScope.CURRENT_USER_NAME = null;
                    $location.path('/');
                });
        }

        //read message and show it
        if($location.search()['error']){
            messagePrompt.error($location.search()['error']);
            $location.search('error', null);
        }
        if($location.search()['success']){
            messagePrompt.success($location.search()['success']);
            $location.search('success', null);
        }
    }]);

});
