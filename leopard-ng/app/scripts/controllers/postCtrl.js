define(['app', 'service', 'config'], function (app) {

    'use strict';

    app.controller('postCtrl', ['configFactory', 'requestProxy', 'config', '$scope'
        , '$routeParams', '$location', '$sce'
        , function(configFactory, requestProxy, config, $scope, $routeParams, $location
            , $sce){
        var postData = {
                title: null,
                navs: [],
                list: [],
                detail: null,
                category: $routeParams['category'],
                type: $routeParams['type'],
                template: null,
                isList: false,
                isDetail: $routeParams['id']
            },
            postId = $routeParams['id'],
            postConf = {},
            paginationConf = {
                item: null,
                current: 0,
                total: null,
                getData: getData
            };
        $scope.paginationConf = paginationConf;
        $scope.postData = postData;

        //read post config
        postConf = config['postConfig']['navs'][postData.category];
        if(!postConf){
            $location.path('/404');
            return;
        }
        postData.navs = postConf['childs'];
        postData.title = postConf['name'];

        //read post request config
        var postType = (function(){
                var t = postConf['childs'];
                for(var i in t){
                    if(t[i].url == postData.type){
                        postData.childTitle = t[i].name;
                        postData.isList = t[i].list;
                        return t[i].type;
                    }
                }
            })(),
            requestConf = postData.isDetail?
                configFactory(['getPost'], {params: {post_id: postId}})
                : configFactory(['getPosts']
                , {params: {limit: config['postConfig']['pagination']
                    , filter: {type: postType}}});

        //change the template
        if(postId || !postData.isList)
            postData.template = '/views/post/detail.html';
        else
            postData.template = '/views/post/list.html';

        if(postType == null){
            $location.path('/404');
            return;
        }

        //set a function to get data
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
                    if(postId){
                        postData.detail = data;
                        postData.detail.content = $sce.trustAsHtml(data.content);
                    }
                    else if(!postData.isList){
                        if(data[0])
                            postData.detail = $sce.trustAsHtml(data[0].content);
                    }else{
                        postData.list = data;
                    }
                });
        }
        getData();
    }]);
})
