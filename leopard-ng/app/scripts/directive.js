define(['app', 'zeroclip', 'service', 'morris' ,'fancybox'], function(app, ZeroClipboard){

    'use strict';
    /*Name: fold element base on 'slideToggle' of jquery
     *Author: Peach
     *Time: 2014-5-6
    */
    app.directive('folding', function(){
        return {
            restrict: 'A',
            link: function($scope, iElm, iAttrs){
                var f = jQuery(iAttrs['folding']);
                iElm.click(function(){
                    f.stop(true).slideToggle();
                });
            }
        }
    })
    /*Name: watch router change
     *Author: Peach
     *Time: 2014-5-6
    */
    app.directive('matchNavbar', ['$location', function ($location) {
        return {
            restrict: 'A',
            link: function postLink($scope, iElm, iAttrs){
                $scope.checkChilds = function(){
                    //check navs is or no ready
                    var t = jQuery('li[data-match-route]', iElm);
                    if(!t.size())
                        return false;
                    //check scope's values is or no ready
                    if(t.eq(0).attr('data-match-route').indexOf('{{') != -1)
                        return false;
                    return true;
                }

                var watcher = $scope.$watch('checkChilds()', function(data){
                    if(data){
                        $scope.$watch(function (){
                            return $location.path();
                        }, function(newValue, oldValue){
                            //if this attr is 'true', let scrollTop = 0
                            if(iAttrs['matchNavbar']){
                                jQuery('html,body').stop(true).animate({'scrollTop': 0}, 300);
                            }
                            jQuery('li[data-match-route]', iElm).each(function(k, li){
                                var $li = angular.element(li),
                                    pattern = $li.attr('data-match-route'),
                                    regexp = new RegExp('^' + pattern + '$', ['i']);
                                if(regexp.test(newValue)){
                                    $li.addClass('active');
                                    var $collapse = $li.find('.collapse.in');
                                    if ($collapse.length)
                                        $collapse.collapse('hide');
                                }else{
                                    $li.removeClass('active');
                                }
                            });
                        });
                        watcher();
                    }
                })
            }
        };
    }]);
    /*Name: banner directive
     *Author: Peach
     *Time: 2014-5-15
    */
    app.directive('bannerShow',['$timeout', 'config', function($timeout, config){
        return {
            restrict: 'A',
            link: function($scope, iElm, iAttrs){
                var loader = iElm.find('#banner-load'),
                    imgCount = 0, //number of loaded image
                    loadTime = 0, //caculation load time
                    imgs = [],  //save all images
                    imgNum = 0,  //save the number of img
                    changeTime = config['bannerConfig'].changeTime,  //how long to change the image
                    limitTime = config['bannerConfig'].loadTime/500;  //set limit load time (500ms/time)

                //set a function for watch value
                $scope.checkConfig = function(){
                    if($scope.$eval(iAttrs['bannerShow'])
                        && iElm.find('#banner-list li').size() != 0)
                        return $scope.$eval(iAttrs['bannerShow']);
                    return false;
                }

                var configWatcher = $scope.$watch('checkConfig()', function(data){
                    imgNum = data.length;
                    if(data){
                        imgs = data;
                        for(var i=0;i<imgs.length;i++){
                            var img = new Image();

                            img.onload = function(){
                                imgCount++;
                            }
                            if(imgs[i])
                                img.src = imgs[i].src;
                            else
                                imgNum--;
                        }
                        //start load banner
                        loadBanner();
                        //remove watcher
                        configWatcher();
                    }
                });

                function loadBanner(){
                    if(loadTime >= limitTime){
                        loader.addClass('failure');
                        return;
                    }
                    if(imgCount < imgNum){
                        loadTime ++;
                        $timeout(loadBanner, 500);
                        return;
                    }

                    var box = iElm.find('#banner-list'),
                        list = box.find('li'),
                        selectBox = iElm.find('#banner-select'),
                        selects = selectBox.find('li'),
                        index = 0,
                        timer = null;
                    //if there not have image, just remove the loader
                    if(list.size() == 0){
                        removeLoader();
                        return;
                    }

                    //init the banners
                    list.eq(index).css({'zIndex': 2, 'opacity': 1});
                    selects.eq(index).addClass('active');

                    //set a function for change
                    function change(i){
                        if(i == index)
                            return;
                        list.eq(i).css({'zIndex': 3}).stop(true)
                            .animate({'opacity': 1}, 300, function(){
                                list.eq(index).css({'zIndex': 1, 'opacity': 0});
                                list.eq(i).css('zIndex', 2);
                                selects.eq(index).removeClass('active');
                                selects.eq(i).addClass('active');
                                index = i;
                            });
                    }

                    //set tow function to operate timer
                    function cancelTimer(){
                        $timeout.cancel(timer);
                    }
                    function setTimer(){
                        $timeout.cancel(timer);
                        timer = $timeout(autoChange, changeTime);
                    }

                    //set a function for auto change
                    function autoChange(){
                        var target = index + 1>=list.size()?0: index + 1;
                        change(target);
                        setTimer();
                    }

                    //add mouseover event
                    box.mouseover(cancelTimer);
                    box.mouseleave(setTimer);
                    selectBox.mouseover(cancelTimer);
                    selectBox.mouseleave(setTimer);

                    //add click event
                    selects.click(function(){
                        if(index == jQuery(this).index())
                            return;
                        change(jQuery(this).index());
                    });

                    //remove loader and show banner
                    function removeLoader(){
                        loader.fadeOut(500, function(){
                            loader.remove();
                        })
                    }
                    removeLoader();
                    box.animate({'opacity': 1}, 800);
                    selectBox.animate({'opacity': 1}, 800);

                    //start auto change
                    setTimer();
                }
            }
        }
    }]);
    /*Name: morris render directive
     *Author: Peach
     *Time: 2014-5-15
     *See: useage: <element data-morris-render="your configs"></element>
    */
    app.directive('morrisRender', ['$timeout', '$filter', 'config', function($timeout, $filter, config){
        return {
            restrict: 'A',
            link: function($scope, iElm, iAttrs) {
                var conf = {
                    type: null,
                    xkeys: [],
                    labels: [],
                    colors: [],
                    values: []
                };
                //set a function for watch
                $scope.checkConfig = function(){
                    return $scope.$eval(iAttrs['morrisRender']);
                }
                //watch the config
                var watcher = $scope.$watch('checkConfig()', function(data){
                    if(data){
                        conf.values = data['data'];
                        conf.type = data['type'] || 'donut';
                        conf.xkeys = data['xkeys'] || ['label', 'value'];
                        conf.labels = data['labels'] || ['X', 'Y'];
                        conf.colors = data['colors'] || config['morrisConfig'].colors;
                        $timeout(renderMorris, 300);
                        //remove the watcher
                        watcher();
                    }
                });

                function renderMorris(){
                    iElm.css('opacity', 0);
                    var t = conf.type;
                    if(t == 'donut'){
                        Morris.Donut({
                            element: iElm,
                            data: conf.values,
                            colors: conf.colors,
                            formatter: function(y, data){
                                if(y == 0.0001)
                                    y = 0;
                                if(data.type == 'percent')
                                    return y + '%';
                                else if(data.type == 'money')
                                    return $filter('currency')(y, '￥');
                                else
                                    return y;
                            }
                        });
                    }else if(t == 'bar'){
                        Morris.Bar({
                            element: iElm,
                            data: conf.values,
                            xkey: 'y',
                            ykeys: conf.xkeys,
                            labels: conf.labels,
                            barColors: conf.colors,
                            yLabelFormat: function(x){
                                return $filter('currency')(x, '') + ' \u5143'; //元
                            }
                        });
                    }
                    iElm.animate({'opacity': 1}, 300);
                }
            }
        };
    }]);
    /*Name: custome on blur directive
     *Author: Peach
     *Time: 2014-5-15
     *See: useage: <element data-event-blur="your callback function"></element>
    */
    app.directive('eventBlur', function(){
        return {
            link: function($scope, iElm, iAttrs){
                iElm.bind('blur', function(){
                    $scope.$apply(iAttrs['eventBlur']);
                });
            }
        }
    });
    /*Name: flash clipboard directive
     *Author: Peach
     *Time: 2014-5-15
     *See: useage: <element data-clip-board="your callback function"
     *     data-clipboard-target="the container that you want to coping"></element>
    */
    app.directive('clipBoard', ['config', 'messagePrompt', function(config, messagePrompt){
        return {
            restrict: 'A',
            link: function($scope, iElm, iAttrs) {
                ZeroClipboard.config(config['zeroClipConfig']);
                var z = new ZeroClipboard(iElm);
                z.on('aftercopy', function(){
                    if(iAttrs['clipBoard'])
                        $scope.$apply(iAttrs['clipBoard']);
                    messagePrompt.success('\u590D\u5236\u6210\u529F !');  //复制成功
                });
            }
        };
    }]);
    /*Name: form produce directive
     *Author: Peach
     *Time: 2014-5-16
     *See: need form control, just like input/textarea/checkbox
    */
    app.directive('formProduce', ['configFactory', 'warningForm', 'requestProxy'
        , function(configFactory, warningForm, requestProxy){
        return {
            restrict: 'A',
            scope: true,
            controller: ['$scope', '$element', '$attrs', function($scope, $element, $attrs) {
                var controls = {},
                    values = {},
                    onlyFun = null,
                    elmCount = 0;

                this.addControl = function(name, control){
                    if(controls[name] === undefined)
                        elmCount++;
                    controls[name] = control;
                }
                this.setValue = function(name, value){
                    values[name] = value;
                }
                this.setOnlyFun = function(fun){
                    onlyFun = fun;
                }
                $element.submit(startSubmit);
                this.startSubmit = startSubmit;

                function startSubmit(onlyCheck){
                    for(var i in values){
                        //if not require, don't check it
                        if(!controls[i].require)
                            continue;
                        //check is null
                        if(!values[i]){
                            warningForm($scope, controls[i].element, controls[i].label + '\u4E0D\u80FD\u4E3A\u7A7A !');  //不能为空
                            return false;
                        }
                        //check is seem to another one
                        if(controls[i].seemAs && values[i] != values[controls[i].seemAs]){
                            warningForm($scope, controls[i].element, (controls[i].label
                                + '\u4E0E' + controls[controls[i].seemAs].label
                                + '\u5FC5\u987B\u4E00\u81F4 !'));  //与...必须一致
                            return false;
                        }
                        //check is overflow
                        if(controls[i].max && values[i]*1>controls[i].max){
                            warningForm($scope, controls[i].element, controls[i].label
                                + '\u4E0D\u80FD\u8D85\u8FC7 ' + controls[i].max + ' !');  //不能超过
                            return false;
                        }
                        if(controls[i].min && values[i]*1<controls[i].min){
                            warningForm($scope, controls[i].element, controls[i].label
                                + '\u4E0D\u80FD\u4F4E\u4E8E ' + controls[i].min + ' !');  //不能低于
                            return false;
                        }
                        //check the RegExp
                        if(controls[i].pattern){
                            var t = controls[i].pattern.split('/'),
                                r = new RegExp(t[1], t[t.length-1]);
                            if(!r.test(values[i])){
                                warningForm($scope, controls[i].element, controls[i].warning || (controls[i].label + '\u4E0D\u7B26\u5408\u89C4\u8303 !'));  //不符合规范
                                return false;
                            }
                        }
                    }
                    var requestConf = {
                            keyName: $scope.formConf.keyName,
                            data: values
                        };

                    //check is exist
                    var existCount = 0,
                        checkCount = 0;
                    for(var i in values){
                        checkCount++;
                        if(controls[i].isExist){
                            existCount++;
                            var checkConf = configFactory([controls[i].isExist], {params: {}}),
                                tempKey = i;
                            checkConf.params[i] = values[i];
                            requestProxy(checkConf)
                                .success(function(data){
                                    if(data[tempKey]){
                                        warningForm($scope, controls[tempKey].element, controls[tempKey].label
                                        + '\u5DF2\u88AB\u4F7F\u7528 !');  //已被使用
                                    }else if(elmCount == checkCount)
                                        request();
                                });
                        }
                    }

                    if(!existCount)
                        request();

                    function request(){
                        //if only need check the form, dont' request
                        if(onlyCheck == true && onlyFun)
                            return $scope.$eval(onlyFun);
                        //if the config have a function for excuting, don't request
                        if($scope.formConf.fun){
                            $scope.formConf.fun();
                            return false;
                        }
                        var btnTxt = (function(){
                            //get all submit element
                            var e = jQuery($element).find('input[type=submit],button:not(button[type=button])'),
                                t = [];

                            for(var i=0;i<e.size();i++){
                                t.push(e.eq(i).val() || e.eq(i).html());
                                if(e.eq(i).val())
                                    e.eq(i).val('提交中...');
                                else
                                    e.eq(i).html('提交中...');
                                e.attr('disabled', 'disabled');
                            }
                            return t;
                        })();
                        requestProxy(requestConf)
                            .success(function(d, s, h, c){
                                if($scope.formConf['success'])
                                    $scope.formConf['success'](d, s, h, c);
                                resetBtn(btnTxt);
                            })
                            .error(function(d, s, h, c){
                                if($scope.formConf['error'])
                                    $scope.formConf['error'](d, s, h, c);
                                resetBtn(btnTxt);
                            });
                    }

                    function resetBtn(btnTxt){
                        var e = jQuery($element).find('input[type=submit],button:not(button[type=button])');

                        for(var i=0;i<e.size();i++){
                            if(e.eq(i).val())
                                e.eq(i).val(btnTxt[i]);
                            else
                                e.eq(i).html(btnTxt[i]);
                            e.removeAttr('disabled');
                        }
                    }
                    return false;
                }
            }],
            link: function($scope, iElm, iAttrs, controller) {
                //set a function for watch
                $scope.checkConfig = function(){
                    return $scope.$eval(iAttrs['formProduce']);
                }
                //watch the config
                var watcher = $scope.$watch('checkConfig()', function(conf){
                    $scope.formConf = conf;
                });
            }
        };
    }]);
    /*Name: normal input directive
     *Author: Peach
     *Time: 2014-5-16
     *See: require form produce
    */
    app.directive('inputProduce',['configFactory', 'warningForm', 'requestProxy', function(configFactory, warningForm, requestProxy){
        return {
            restrict: 'A',
            scope: true,
            require: '^?formProduce',
            link: function($scope, iElm, iAttrs, formProduce) {
                //set a function for watch
                $scope.checkConfig = function(){
                    return $scope.$eval(iAttrs['inputProduce']);
                }
                //watch the config
                var watcher = $scope.$watch('checkConfig()', function(conf){
                    if(conf){
                        var control = {
                                label: conf.label,
                                pattern: conf.pattern,
                                warning: conf.warning,
                                require: conf.require,
                                seemAs: conf.seemAs,
                                isExist: conf.isExist,
                                min: conf.min,
                                max: conf.max,
                                element: iElm
                            },
                            name = conf.name;
                        formProduce.addControl(name, control);

                        $scope.getVal = function(){
                            return $scope.$eval(iAttrs['ngModel']);
                        }
                        $scope.$watch('getVal()', function(data){
                            formProduce.setValue(name, jQuery.trim(data));
                        });
                        if(conf.isExist){
                            iElm.bind('blur', function(){
                                if(!iElm.val())
                                    return;
                                if(control.pattern){
                                    var t = control.pattern.split('/'),
                                        r = new RegExp(t[1], t[t.length-1]);
                                    if(!r.test(iElm.val()))
                                        return;
                                }
                                var checkConf = configFactory([conf.isExist], {params: {}});
                                checkConf.params[name] = jQuery.trim(iElm.val());
                                requestProxy(checkConf)
                                    .success(function(data){
                                        if(data[name])
                                            warningForm($scope, iElm, conf.label
                                            + '\u5DF2\u88AB\u4F7F\u7528 !');  //已被使用
                                    });
                            });
                        }
                        //watcher();
                    }
                }, true);

            }
        };
    }]);
    /*Name: phone verify directive
     *Author: Peach
     *Time: 2014-5-16
     *See: require form produce
    */
    app.directive('phoneProduce',['messagePrompt', 'configFactory', 'warningForm', 'requestProxy', '$timeout'
        , function(messagePrompt, configFactory, warningForm, requestProxy, $timeout){
        return {
            restrict: 'A',
            scope: true,
            require: '^?formProduce',
            link: function($scope, iElm, iAttrs, formProduce) {
                //set a function for watch
                $scope.checkConfig = function(){
                    return $scope.$eval(iAttrs['phoneProduce']);
                }
                //watch the config
                var watcher = $scope.$watch('checkConfig()', function(conf){
                    if(conf){
                        var control = {
                                label: conf.label,
                                pattern: conf.pattern,
                                warning: conf.warning,
                                require: conf.require,
                                element: iElm
                            },
                            name = conf.name,
                            requestConf = configFactory([conf.keyName]),
                            sendBtn = angular.element(iAttrs['phoneSend']),
                            sendTxt = sendBtn.val() || sendBtn.html(),
                            sendTimer = null;

                        if(requestConf.method == 'GET')
                            requestConf['params'] = {};
                        else
                            requestConf['data'] = {};
                        formProduce.addControl(name, control);

                        $scope.getVal = function(){
                            return ($scope.$eval(iAttrs['ngModel']));
                        }
                        $scope.$watch('getVal()', function(data){
                            var t = jQuery.trim(data);
                            formProduce.setValue(name, t);
                            if(requestConf.method == 'GET')
                                requestConf.params[name] = t;
                            else
                                requestConf.data[name] = t;
                        });

                        sendBtn.click(function(){
                            if(sendBtn.attr('disabled'))
                                return;
                            if(!iElm.val() && control.pattern){
                                warningForm($scope, iElm, control.label + '\u4E0D\u80FD\u4E3A\u7A7A !');  //不能为空
                                return;
                            }
                            if(control.pattern){
                                var t = control.pattern.split('/'),
                                    r = new RegExp(t[1], t[t.length-1]);
                                if(!r.test(iElm.val())){
                                    warningForm($scope, iElm, control.warning || (control.label + '\u4E0D\u7B26\u5408\u89C4\u8303 !'));  //不符合规范
                                    return;
                                }
                            }
                            if(conf.isExist){
                                var checkConf = configFactory([conf.isExist], {params: {}});
                                checkConf.params[name] = iElm.val();
                                requestProxy(checkConf)
                                    .success(function(data){
                                        if(data[name])
                                            warningForm($scope, iElm, conf.label
                                            + '\u5DF2\u88AB\u4F7F\u7528 !');  //已被使用
                                        else
                                            request();
                                    });
                            }else
                                request();

                            function request(){
                                var conf = angular.fromJson(iAttrs['phoneSendValidate']);
                                if(typeof(conf) == 'object')
                                    angular.extend(requestConf['params'], conf);

                                requestProxy(requestConf)
                                    .success(function(data){
                                        messagePrompt.success(data.message);
                                    })
                                    .error(function () {
                                        $timeout.cancel(sendTimer);
                                        sendBtn.removeAttr('disabled');
                                        sendBtn.val()?sendBtn.val(sendTxt): sendBtn.html(sendTxt);
                                    });
                                sendBtn.attr('disabled', 'disabled');
                                startTimeout(60);
                            }
                        });
                        //watcher();
                    }
                    function startTimeout(t){
                        if(!t){
                            sendBtn.removeAttr('disabled');
                            sendBtn.val()?sendBtn.val(sendTxt): sendBtn.html(sendTxt);
                            return;
                        }
                        var str = '\u8BF7\u7B49\u5F85' + t-- + '\u79D2';
                        sendBtn.val()?sendBtn.val(str): sendBtn.html(str);
                        sendTimer = $timeout(function(){startTimeout(t)}, 1000);
                    }
                });
            }
        };
    }]);
    /*Name: only check form directive
     *Author: Peach
     *Time: 2014-5-28
     *See: require form produce
    */
    app.directive('formOnlyCheck',['requestProxy', function(requestProxy){
        return {
            restrict: 'A',
            require: '^?formProduce',
            link: function($scope, iElm, iAttrs, formProduce) {
                formProduce.setOnlyFun(iAttrs['formOnlyCheck']);

                iElm.click(function(){
                    formProduce.startSubmit(true);
                });
            }
        };
    }]);
    /*Name: list filter directive, contain timer and your types
     *Author: Peach
     *Time: 2014-5-17
     *See: require a view that list_filter.html
    */
    app.directive('filterProduce', ['config', function(config){
        return {
            restrict: 'A',
            scope: true,
            replace:true,
            templateUrl: 'views/list_filter.html',
            controller: ['$scope', '$element', '$attrs', function($scope, $element, $attrs) {
                var filterConf = {
                        start_date: null,
                        end_date: null,
                        day: null
                    },
                    quickConf = [
                        {
                            name: '\u4E0D\u9650',  //不限
                            value: null
                        },
                        {
                            name: '\u4ECA\u5929',  //今天
                            value: 1
                        },
                        {
                            name: '\u4E00\u5468', //一周
                            value: 7
                        },
                        {
                            name: '\u4E00\u4E2A\u6708',  //一个月
                            value: 30
                        },
                        {
                            name: '\u4E09\u4E2A\u6708',  //三个月
                            value: 90
                        },
                        {
                            name: '\u534A\u5E74', //半年
                            value: 180
                        }
                    ];
                $scope.filterConf = filterConf;
                $scope.quickConf = quickConf;

                $scope.quickSelect = function(val){
                    filterConf.day = val;
                    filterConf.start_date = null;
                    filterConf.end_date = null
                    $scope.startFilter(filterConf);
                }

                $scope.timeSelect = function(){
                    filterConf.day = null;
                    $scope.startFilter(filterConf);
                }

                $scope.typeSelect = function(n, val){
                    if(!val)
                        delete(filterConf[n]);
                    else
                        filterConf[n] = val;
                    $scope.startFilter(filterConf);
                }

            }],
            link: function($scope, iElm, iAttrs, controller) {
                //set a function for watch
                $scope.watchConfig = function(){
                    return $scope.$eval(iAttrs['filterProduce']);
                }
                //start watch
                var watcher = $scope.$watch('watchConfig()', function(data){
                    if(data){
                        $scope.filterTypes = data.types;
                        $scope.startFilter = data.getData;
                        watcher();
                    }
                });
            }
        };
    }]);
    /*Name: pagination produce
     *Author: Peach
     *Time: 2014-5-18
    */
    app.directive('paginationProduce', function(){
        return {
            restrict: 'A',
            require: '^?pagination',
            template: '<div data-pagination previous-text="上一页" next-text="下一页"'
                + ' items-per-page="paginationConf.item"'
                + ' page="paginationConf.current" max-size="5"'
                + ' total-items="paginationConf.total" on-select-page="getData(page)"'
                + '></div>',
            link: function($scope, iElm, iAttrs, controller) {
                //set a function for watch
                $scope.checkConfig = function(){
                    return $scope.$eval(iAttrs['paginationProduce']);
                }
                //watch config
                var watcher = $scope.$watch('checkConfig()', function(data){
                    if(data){
                        $scope.paginationConf = data;
                        $scope.getData = data.getData;
                    }
                });
            }
        };
    });
    /*Name: fancybox directive
     *Author: Peach
     *Time: 2014-5-28
    */
    app.directive('fancyBox', function(){
        return {
            link: function($scope, iElm, iAttrs){
                var type = iAttrs['fancyBox'];
                var obj = null;

                if(!type){
                    obj = iElm;
                    render();
                }
                else{
                    $scope.getArray = function(){
                        return $scope.$eval(iAttrs['fancyBox']);
                    }

                    var dataWatch = $scope.$watch('getArray()', function(data){
                        if(data){
                            obj = iElm[0].getElementsByTagName('a');
                            render();
                            dataWatch();
                        }
                    });
                }

                function render(){
                    angular.element(obj).fancybox({
                        maxWidth: 700,
                        minWidth: 500,
                        autoSize: true
                    });
                }
            }
        }
    });
    /*Name: bank number directive
     *Author: Peach
     *Time: 2014-6-3
    */
    app.directive('bankNumber', function(){
        return {
            link: function($scope, iElm, iAttrs){
                var container = null;
                iElm.keyup(function(){
                    if(iElm.val())
                        container.html(showBankcard(iElm.val())).show();
                    else
                        container.hide();
                });
                iElm.blur(function(){
                    container.remove();
                });
                iElm.focus(function(){
                    container = !container?angular.element('<span class="_bankcard-upper"></span>'): container;
                    container.css({'top': iElm.offset().top - iElm.outerHeight() - 2,
                        'left': iElm.offset().left,});
                    angular.element('body').append(container);
                    if(iElm.val())
                        container.html(showBankcard(iElm.val())).show();
                    else
                        container.hide();
                });
                function showBankcard(input){
                    if(!/^[0-9]*$/.test(input))
                        return '银行卡号不合法！';
                    else{
                        for(var i=4;i<input.length;i+=4){
                            var front = input.substring(0, i);
                            var back = input.substring(i);
                            input = front + ' ' + back;
                            i++;
                        }
                        return input;
                    }
                }
            }
        }
    });
    /*Name: watch router to show or hide element
     *Author: Peach
     *Time: 2014-6-20
    */
    app.directive('toggleRoute', ['$location', function ($location) {
        return {
            restrict: 'A',
            link: function postLink($scope, iElm, iAttrs){
                $scope.$watch(function (){
                    return $location.path();
                }, function(newValue, oldValue){
                    var conf = jQuery.parseJSON(iAttrs['toggleRoute']),
                        pattern = conf.match;
                    for(var i in pattern){
                        if(typeof(pattern[i]) != 'string')
                            return;
                        var regexp = new RegExp('^' + pattern[i] + '$', ['i']);
                        if(regexp.test(newValue)){
                            conf.show?iElm.show(): iElm.hide();
                            return;
                        }
                    }
                    iElm.show();
                });
            }
        };
    }]);
    /*Name: dialog
     *Author: Peach
     *Time: 2014-8-12
    */
    app.directive('toggleDialog', ['$document', function ($document) {
        return {
            restrict: 'A',
            link: function postLink($scope, iElm, iAttrs){
                var conf = JSON.parse(iAttrs['toggleDialog']),
                    target = jQuery(conf.box),
                    close = jQuery(conf.close);

                iElm.click(function(ev){
                    target.toggle();
                    event.stopPropagation();
                });
                target.click(function(ev){
                    event.stopPropagation();
                });
                $document.click(function(){
                    target.hide();
                });
                close.click(function(){
                    target.hide();
                });
            }
        };
    }]);
})
