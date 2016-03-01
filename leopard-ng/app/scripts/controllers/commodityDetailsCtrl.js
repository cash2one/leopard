define(['app', 'service'], function (app) {

    'use strict';

    app.controller('commodityDetailsCtrl', ['configFactory', 'financeTools'
        , 'requestProxy', 'messagePrompt', '$scope', '$routeParams', '$modal'
        , '$location', '$rootScope', '$sce', '$interval', 'config'
        , function(configFactory, financeTools, requestProxy, messagePrompt, $scope
            , $routeParams, $modal, $location, $rootScope, $sce, $interval, config){

        var productDetailControls = {
                conf: {
                    //select config
                    keyName: 'payProductOrdery'
                },
                buyNumber: {
                        label: '购买数量',
                        name: 'buy_number',
                        max: 100,
                        min: 1,
                        pattern: '/^\\d+$/',
                        require: true
                },
                models: {
                    
                }
            },
            products = {
                info: {},
                user: {},
            },
            buyModal = null,
            getProductConf = configFactory(['getProductDetail'],
                {params: {commodity_id: $routeParams['id']}});


        //set submit function
        productDetailControls.conf['fun'] = openModal;

        $scope.productDetailControls = productDetailControls;
        $scope.products = products;

         //set a modal
        $scope.openModal = openModal;

        function getData(){
            //get product information
            requestProxy(getProductConf)
                .success(function(data){
                    products.info = data;
                    if (data.number > 0){
                        productDetailControls.models.buy_number = 1;
                    }else{
                        productDetailControls.models.buy_number = 0;
                    }
                    products.info.details = $sce.trustAsHtml(data.details);
                })
                .error(function(){
                    $location.path('/404');
                });

                //get user's information
            if($scope.CURRENT_USER_ID)
                requestProxy({keyName: 'getUser'})
                    .success(function(data){
                        products.user = data;
                });
        }
        getData();

        // watch the user id to get user information
        $scope.$watch('CURRENT_USER_ID', function (id) {
            if(id){
                requestProxy({keyName: 'getUser'})
                    .success(function(data){
                        products.user = data;
                    });
            }else{
                products.user = {};
            }
        })


        function openModal(){
            if(!$scope.CURRENT_USER_ID){
                $location.path('/login');
                messagePrompt.forbidden('请先登录后再进行投资 !');
                return;
            }
            
            if(buyModal){
                buyModal.close();
            }

            buyModal = $modal.open({
                templateUrl: 'pay_commodity_modal.html',
                controller: ['$scope', '$modalInstance', 'config', 'messagePrompt', 'configFactory', 'requestProxy'
            , buyModalIns],
                resolve: {
                }
            });
        }

        //set a modal controller
        var buyModalIns = function($scope, $modalInstance
            ,config, messagePrompt, configFactory, requestProxy){

            var commodity = {
                    is_material: products.info.type == 200,
                    addressee: null,
                    phone: null,
                    address: null,
                    description: null,
                    number: null,
                    tradePass: null,
                    amount: productDetailControls.models.buy_number * products.info.price,
                    config: config['platformConfig']['tradePass']['invest'],
                },
                orderConfig = configFactory(['payProductOrdery'],
                    {params: {order_id: $routeParams['id']}});

            $scope.commodity = commodity;

            $scope.ok = function () {
                if (!(commodity.addressee && commodity.phone &&
                         commodity.address) && commodity.is_material){
                    messagePrompt.forbidden('请把收货信息填写完整 !');
                    return;
                }
                if(commodity.config && !commodity.tradePass){
                    messagePrompt.forbidden('请先输入交易密码 !');
                    return;
                }

                orderConfig.data = {
                    buy_number: productDetailControls.models.buy_number,
                    trade_password: commodity.tradePass,
                    addressee: commodity.addressee,
                    address: commodity.address,
                    phone: commodity.phone,
                    description: commodity.description

                }
                requestProxy(orderConfig)
                    .success(function(data){
                        messagePrompt.success(data.message);
                        $modalInstance.close();
                    });
                commodity.tradePass = null; 
            };
            $scope.cancel = function () {
                $modalInstance.dismiss();
                commodity.tradePass = null;
            };
        };

    }]);
})
