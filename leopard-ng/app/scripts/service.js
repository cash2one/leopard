define(['app'], function(app){

    'use strict';

    /*Name: http request proxy
     *Author: Peach
     *Time: 2014-5-5
    */
    app.factory('requestProxy', ['messagePrompt', 'config', '$http', '$location'
        , '$timeout', '$document'
        , function(messagePrompt, config, $http, $location, $timeout, $document){
        return function(arg){
            var k = arg['keyName'] || null,
                conf = {};
            //copy config to cancel relationship for original object
            jQuery.extend(true, conf, arg);

            if(k){
                var t = config['resConfig'][k];
                conf['url'] = t['url'];
                conf['method'] = t['method'];
                delete conf['keyName'];
            }

            function setParams(conf){
                var l = conf.url.split(':'),
                    d = conf.params;
                for(var i=1;i<l.length;i++){
                    var a = l[i].split('/');
                        k = a[0];
                    if(d[k]){
                        l[i] = d[k];
                        for(var j=1;j<a.length;j++){
                            l[i] += '/' + a[j];
                        }
                        delete(d[k]);
                    }
                    else
                        console.error('Missing parameter "' + k + '"!');
                }
                conf.url = l.join('');

                return conf;
            }

            if(conf.url.indexOf(':', conf.url.indexOf('http:')?-1: 5) != -1){
                conf = setParams(conf);
            }

            if(conf.method == "GET")
            {
                conf.url += "?" + (new Date()).getTime();
            }

            var r = $http(conf);

            r.error(function(d, s, h, c){
                if(d.message)
                {
                    if (s == 406 || s.status == 406){
                        $location.url('/406')
                    }
                    else{
                        messagePrompt.error(d.message);
                    }
                }
                if(s == 403 || s.status == 403){
                    var p = $location.url(),
                        r = $location.search()['redirectURL'];

                    if(!r)
                        $location.url('/login').search({'redirectURL': p});
                    else
                        $location.url('/login').search('redirectURL', r);

                    if(jQuery('body').css('display') == 'none')
                        jQuery($document[0].body).fadeIn();
                }
            });

            return r;
        }
    }]);
    /*Name: finance tools
     *Author: Peach
     *Time: 2014-5-15
    */
    app.factory('financeTools', function(){
        return {
            //the interest rate of each stage
            getRepaymentPlan: function(rate, amount, periods, type){
                var plans = [];
                rate /= 100; //month interest

                if(type == 'average_captial_plus_interest'){
                    var tempPow = Math.pow((1 + rate), periods*1);
                    var monthAmount = amount * rate *  tempPow / (tempPow-1);

                    for (var i=0; i<periods; i++){
                        var interest = amount * rate;
                        amount = amount - monthAmount + interest;

                        plans.push({
                            periods: i+1,
                            monthInterest: monthAmount,
                            monthAmount: monthAmount - interest,
                            interest: interest,
                            amount: monthAmount * (periods - i -1)
                        });
                    }
                }else if(type == 'one_only'){
                    var interest = rate * amount * periods;

                    plans.push({
                        periods: periods,
                        monthInterest: interest*1 + amount*1,
                        monthAmount: amount,
                        interest: interest,
                        amount: 0
                    });
                }else if(type == 'interest_first'){
                    var interest = rate * amount * periods;

                    plans.push({
                        periods: 1,
                        monthInterest: interest,
                        monthAmount: 0,
                        interest: interest,
                        amount: amount
                    },{
                        periods: periods,
                        monthInterest: amount,
                        monthAmount: amount,
                        interest: 0,
                        amount: 0
                    })
                }else if(type == 'capital_final'){
                    var interest = rate * amount * periods;
                    var mInterest = rate * amount;

                    for(var i=1;i<=periods;i++){
                        plans.push({
                            periods: i,
                            monthInterest: i==periods?mInterest*1 + amount*1: mInterest,
                            monthAmount: i==periods?amount: 0,
                            interest: mInterest,
                            amount: i==periods?0: amount*1 + mInterest*(periods-i)
                        })
                    }
                }else if(type == 'average_capital'){
                    var monthAmount = amount / periods;
                    var interest = amount * rate;
                    for(var i=1;i<=periods;i++){
                        plans.push({
                            periods: i,
                            amount: amount,
                            interest: interest,
                            monthInterest: interest / periods + monthAmount * 1,
                            monthAmount: monthAmount * 1
                        })
                    }
                }
                return plans;
            },
            //the interest rate of each stage
            getInterest: function(rate, amount, periods, type, reward, isDaily){
                var interest = 0;
                rate /= 100;

                if(type == 'average_captial_plus_interest'){
                    interest = amount * rate * Math.pow(1 + rate, periods) / (Math.pow(1 + rate, periods) - 1) * periods - amount;
                }else if(type == 'one_only'){
                    interest = amount * rate * periods;
                }else if(type == 'interest_first'){
                    interest = amount * rate * periods;
                }else if(type == 'capital_final'){
                    interest = amount * rate * periods;
                }else if(type == 'average_capital'){
                    interest = amount * rate * periods;
                }
                if(reward)
                    interest += amount * reward / 100;
                return interest;
            },
            getUpperAmount: function(dValue, maxDec){
                if(dValue == '')
                    return;
                dValue = dValue.toString().replace(/,/g, ""); dValue = dValue.replace(/^0+/, "");
                if (dValue == "") { return "零元整"; }
                else if (isNaN(dValue)) { return "错误：金额不是合法的数值！"; }

                var minus = "";
                var CN_SYMBOL = "";
                if (dValue.length > 1)
                {
                    if (dValue.indexOf('-') == 0) { dValue = dValue.replace("-", ""); minus = "负"; }
                    if (dValue.indexOf('+') == 0) { dValue = dValue.replace("+", ""); }
                }
                var vInt = ""; var vDec = "";
                var resAIW;
                var parts;
                var digits, radices, bigRadices, decimals;
                var zeroCount;
                var i, p, d;
                var quotient, modulus;
                var NoneDecLen = (typeof(maxDec) == "undefined" || maxDec == null || Number(maxDec)
                    < 0 || Number(maxDec) >
                    5);
                parts = dValue.split('.');
                if (parts.length > 1)
                {
                    vInt = parts[0]; vDec = parts[1];

                    if(NoneDecLen) { maxDec = vDec.length > 5 ? 5 : vDec.length; }
                    var rDec = Number("0." + vDec);
                    rDec *= Math.pow(10, maxDec); rDec = Math.round(Math.abs(rDec)); rDec /= Math.pow(10, maxDec);
                    var aIntDec = rDec.toString().split('.');
                    if(Number(aIntDec[0]) == 1) { vInt = (Number(vInt) + 1).toString(); }
                    if(aIntDec.length > 1) { vDec = aIntDec[1]; } else { vDec = ""; }
                }
                else { vInt = dValue; vDec = ""; if(NoneDecLen) { maxDec = 0; } }
                if(vInt.length > 44) { return "错误：金额值太大了！整数位长【" + vInt.length.toString() + "】超过了上限——44位/千正/10^43（注：1正=1万涧=1亿亿亿亿亿，10^40）！"; }

                digits = new Array("零", "壹", "贰", "叁", "肆", "伍", "陆", "柒", "捌", "玖");
                radices = new Array("", "拾", "佰", "仟");
                bigRadices = new Array("", "万", "亿", "兆", "京", "垓", "杼", "穰" ,"沟", "涧", "正");
                decimals = new Array("角", "分", "厘", "毫", "丝");

                resAIW = "";

                if (Number(vInt) > 0)
                {
                    zeroCount = 0;
                    for (i = 0; i
                        < vInt.length; i++)
                    {
                        p = vInt.length - i - 1; d = vInt.substr(i, 1); quotient = p / 4; modulus = p % 4;
                        if (d == "0") { zeroCount++; }
                        else
                        {
                            if (zeroCount >
                                0) { resAIW += digits[0]; }
                            zeroCount = 0; resAIW += digits[Number(d)] + radices[modulus];
                        }
                        if (modulus == 0 && zeroCount < 4) { resAIW += bigRadices[quotient]; }
                    }
                    resAIW += "元";
                }

                for (i = 0; i < vDec.length; i++) { d = vDec.substr(i, 1); if (d != "0") { resAIW += digits[Number(d)] + decimals[i]; } }

                if (resAIW == "") { resAIW = "零" + "元"; }
                if (vDec == "") { resAIW += "整"; }
                resAIW = CN_SYMBOL + minus + resAIW;
                return resAIW;
            },
            checkBankcard: function (cardNo){
                var deferred = $q.defer();
                jQuery.ajax({
                    url: "https://ccdcapi.alipay.com/validateAndCacheCardInfo.json",
                    dataType: "jsonp",
                    jsonp: "_callback",
                    timeout: 20000,
                    data: '_input_charset=utf-8&cardNo=' + cardNo + '&cardBinCheck=true',
                    success: function(data){
                        deferred.resolve(data);
                    },
                    error: function(data){
                        deferred.reject(data);
                    }
                });
                return deferred.promise;
            }
        }
    });
    /*Name: check user's permission
     *Author: Peach
     *Time: 2014-5-15
     *See: This service is used to detect the user has no privileges, if params is true, if not have redirect
    */
    app.factory('checkPermission', ['requestProxy', 'messagePrompt', '$location'
        , '$rootScope', '$q', '$timeout'
        , function(requestProxy, messagePrompt, $location, $rootScope, $q, $timeout){
        return function(f){
            var deferred = $q.defer();
            $timeout(function () {
                if($rootScope.CURRENT_USER_ID){
                    deferred.resolve();
                }else{
                    requestProxy({keyName: 'checkLogin'}).then(
                        function(data){
                            if(data.data.user_id){
                                $rootScope.CURRENT_USER_ID = data.data.user_id;
                                deferred.resolve();
                            }else{
                                angular.element('html, body').animate({'scrollTop': 0}, 200);
                                if(!f){
                                    var p = $location.url(),
                                        r = $location.search()['redirectURL'];

                                    if(!r)
                                        $location.url('/login').search({'redirectURL': p});
                                    else
                                        $location.url('/login').search('redirectURL', r);
                                }
                                deferred.reject();
                            }
                        }
                    );
                }
            }, 1);

            return deferred.promise;
        }
    }]);
    /*Name: form control warning
     *Author: Peach
     *Time: 2014-5-16
     *Require: plug.less, font-awesome
    */
    app.factory('warningForm', ['$location', '$document', '$timeout', function($location, $document, $timeout){
        return function ($scope, iElm, txt){
            var b = jQuery('<span class="_warning-container"></span>'),
                t = iElm.outerHeight() + iElm.offset().top,
                l = iElm.outerWidth()/2 + iElm.offset().left,
                flickerTime = 0;
            b.css({'top': t, 'left': l})
                .append($('<i class="icon-warning-sign icon-large"></i>'))
                .append('&nbsp;' + txt);
            $document.find('body').append(b);
            iElm.addClass('_warning-base');
            //check the element is or not in the window
            checkPosition();
            function checkPosition(){
                var temp = $document.scrollTop();
                if(temp > t - 100)
                    angular.element('html,body').animate({'scrollTop': t - 100}, 200);
            }
            //set a function for flicker the background of element
            flicker();
            function flicker(){
                if(flickerTime < 4){
                    flickerTime ++;
                    iElm.toggleClass('_warning-flicker');
                    $timeout(flicker, 300);
                }else
                    iElm.focus();
            }
            //watch the 'keydown' and 'blur' event, and remove it when user press key
            var keyHandle = function(){
                    b.remove();
                    iElm.unbind('keydown', keyHandle).unbind('blur', blurHandle);
                    $document.unbind('click', clickHandle);
                },
                blurHandle = function(){
                    b.remove();
                    iElm.unbind('blur', blurHandle).unbind('keydown', keyHandle);
                    $document.unbind('click', clickHandle);
                },
                clickHandle = function(){
                    b.remove();
                    iElm.unbind('blur', blurHandle).unbind('keydown', keyHandle);
                    $document.unbind('click', clickHandle);
                };

            iElm.bind('keydown', keyHandle);
            iElm.bind('blur', blurHandle);
            $timeout(function(){
                $document.bind('click', clickHandle);
            }, 1)

            $scope.$on('$destroy', function(){
                angular.element('._warning-container').remove();
            });
        }
    }]);
    /*Name: create a service to prompt some message
     *Author: Peach
     *Time: 2014-5-16
     *Require: plug.less, font-awesome
    */
    app.factory('messagePrompt', ['$document', '$q', '$timeout', function($document, $q, $timeout){
        return {
            iconClass: null,
            iconColor: null,
            run: function(message, title){
                angular.element('._message-prompt-box').remove();
                var deferred = $q.defer();
                var box = angular.element('<div class="_message-prompt-box"></div>');
                var icon = angular.element('<i></i>');
                var boxTitle = angular.element('<p class="_message-prompt-title"></p>');

                icon.addClass(this.iconClass).css('color', this.iconColor);
                icon.addClass('icon-3x').css({'vertical-align': 'middle'
                    ,'margin': '0 15px 0 5px'});
                boxTitle.html(title || '\u7CFB\u7EDF\u63D0\u793A');  //系统提示
                box.html(message);
                box.prepend(icon).prepend(boxTitle);

                $document.find('body').append(box);
                box.css({'marginLeft': -box.outerWidth()/2, 'width': box.outerWidth()});

                box.animate({'marginTop': -100, 'opacity': 1}, 500, function(){
                    $timeout(function(){
                        box.animate({'marginTop': -50, 'opacity': 0}, 300, function(){
                            box.remove();
                            deferred.resolve();
                        })
                    }, (message.length*100 < 1500?1500: message.length*100));
                })

                return deferred.promise;
            },
            success: function(message, title){
                this.iconClass = 'icon-ok-sign';
                this.iconColor = '#43b39f';
                return this.run(message, title);
            },
            error: function(message, title){
                this.iconClass = 'icon-remove-sign';
                this.iconColor = '#ff5151';
                return this.run(message, title);
            },
            info: function(message, title){
                this.iconClass = 'icon-info-sign';
                this.iconColor = '#419ED3';
                return this.run(message, title);
            },
            warning: function(message, title){
                this.iconClass = 'icon-exclamation-sign';
                this.iconColor = '#DFA744';
                return this.run(message, title);
            },
            forbidden: function(message, title){
                this.iconClass = 'icon-ban-circle';
                this.iconColor = '#D60000';
                return this.run(message, title);
            }
        }
    }]);
    /*Name: config factory service
     *Author: Peach
     *Time: 2014-5-17
    */
    app.factory('configFactory', ['config', function(config){
        return function (k, p){
            var t = getConf(config['resConfig'], 0),
                r = {};

            //find the config from 'config'
            function getConf(c, i){
                if(i >= k.length || !c[k[i]])
                    return null;
                if(i == k.length - 1)
                    return c[k[i]];
                c = c[k[i++]];
                return getConf(c, i);
            }
            //copy config
            for(var i in t)
                r[i] = t[i];
            //add new attribute
            for(var i in p){
                r[i] = p[i];
            }
            return r;
        };
    }]);
    /*Name: filter config factory service
     *Author: Peach
     *Time: 2014-5-18
    */
    app.factory('filterConfigProduce', ['config', function(config){
        return function (k){
            var t = config['statusConfig'][k],
                r = [{name: '全部', value: null}];

            for(var i in t){
                r.push({
                    name: t[i],
                    value: i
                })
            }
            return r;
        };
    }]);
})
