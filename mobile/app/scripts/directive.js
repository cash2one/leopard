define(['ionic'], function(){

  'use strict';

  return angular.module('truffleDirective', [])
    /* form produce directive
     * @date        2015-3-5
     * @author      Peach<scdzwyxst@gmail.com>
     * @see need form control, just like input/textarea/checkbox
    */
    .directive('formProduce', ['messagePrompt', 'requestHandler'
      , '$log'
      , function(messagePrompt, requestHandler, $log){
      return {
        restrict: 'A',
        scope: true,
        controller: ['$scope', '$element', '$attrs'
        , function($scope, $element, $attrs) {
          var controls = {},
              values = {},
              onlyFun = null,
              elmCount = 0;

          this.addControl = function(name, control){
            if(controls[name] === undefined)
              elmCount++;
            controls[name] = control;
            $log.debug('No.' + elmCount
              + ' Form component be registered: '
              + control.label + ' - ' +  name + '');
          }
          this.setValue = function(name, value){
            values[name] = value;
          }
          this.setOnlyFun = function(fun){
            onlyFun = fun;
          }

          // register submit event
          $element.submit(startSubmit);
          this.startSubmit = startSubmit;

          function startSubmit(onlyCheck){
            for(var i in values){
              //if not require, don't check it
              if(!controls[i].require){
                if(!values[i]
                  || values[i].length == 0
                  || typeof(values[i]) == 'object'){
                  continue;
                }
              }
              //check is null
              if(values[i] === ''
                || values[i] === undefined
                || values[i] === null
                || values[i].length == 0){
                messagePrompt.tooltip(controls[i].label + '\u4E0D\u80FD\u4E3A\u7A7A !');  //不能为空
                return false;
              }
              //check is seem to another one
              if(controls[i].seemAs && values[i] != values[controls[i].seemAs]){
                messagePrompt.tooltip((controls[i].label
                  + '\u4E0E' + controls[controls[i].seemAs].label
                  + '\u5FC5\u987B\u4E00\u81F4 !'));  //与...必须一致
                return false;
              }
              //check is overflow
              if(controls[i].max && values[i]*1>controls[i].max){
                messagePrompt.tooltip(controls[i].label
                  + '\u4E0D\u80FD\u8D85\u8FC7 ' + controls[i].max + ' !');  //不能超过
                return false;
              }
              if(controls[i].min && values[i]*1<controls[i].min){
                messagePrompt.tooltip(controls[i].label
                  + '\u4E0D\u80FD\u4F4E\u4E8E ' + controls[i].min + ' !');  //不能低于
                return false;
              }
              //check the RegExp
              if(controls[i].pattern){
                var t = controls[i].pattern.split('/'),
                    r = new RegExp(t[1], t[t.length-1]);
                if(!r.test(values[i])){
                    messagePrompt.tooltip(controls[i].warning || (controls[i].label + '\u4E0D\u7B26\u5408\u89C4\u8303 !'));  //不符合规范
                    return false;
                }
              }
            }
            var requestConf = {
              keyName: $scope.formConf.keyName,
              data: values,
              params: $scope.formConf.params,
              method: $scope.formConf.method
            };

            //check is exist
            var existCount = 0,
                checkCount = 0;
            for(var i in values){
              checkCount++;
              if(controls[i].isExist){
                existCount++;
                var checkConf = {
                      keyName: controls[i].isExist,
                      params: {}
                    },
                    tempKey = i;
                checkConf.params[i] = values[i];
                requestHandler(checkConf)
                  .success(function(data){
                    if(data[tempKey]){
                      messagePrompt.tooltip(controls[tempKey].label
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
              requestHandler(requestConf)
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
          //watch the config
          var watcher = $scope.$watch(iAttrs['formProduce'], function(conf){
            $scope.formConf = conf;
          });
        }
      };
    }])
    /* normal input directive
     * @date        2014-5-16
     * @author      Peach<scdzwyxst@gmail.com>
     * @see require form produce
    */
    .directive('inputProduce',['messagePrompt', 'requestHandler', function(messagePrompt, requestHandler){
      return {
        restrict: 'A',
        scope: true,
        require: '^?formProduce',
        link: function($scope, iElm, iAttrs, formProduce) {
          //watch the config
          var watcher = $scope.$watch(iAttrs['inputProduce'], function(conf){
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

              $scope.$watch(iAttrs['ngModel'], function(data){
                if(angular.isString(data)){
                  jQuery.trim(data);
                }
                formProduce.setValue(name, data);
              }, true);
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
                  var checkConf = {
                      keyName: conf.isExist,
                      params: {}
                  };
                  checkConf.params[name] = jQuery.trim(iElm.val());
                  requestHandler(checkConf)
                    .success(function(data){
                      if(data[name])
                        messagePrompt.tooltip(conf.label
                          + '\u5DF2\u88AB\u4F7F\u7528 !');  //已被使用
                    });
                });
              }
            }
          }, true);

        }
      };
    }])
    /* phone verify directive
     * @date        2014-5-16
     * @author      Peach<scdzwyxst@gmail.com>
     * @see require form produce
    */
    .directive('phoneProduce',['config', 'messagePrompt', 'requestHandler', '$timeout'
      , function(config, messagePrompt, requestHandler, $timeout){
      return {
        restrict: 'A',
        scope: true,
        require: '^?formProduce',
        link: function($scope, iElm, iAttrs, formProduce) {
          var timer = null;
          //watch the config
          var watcher = $scope.$watch(iAttrs['phoneProduce'], function(conf){
            if(conf){
              var control = {
                    label: conf.label,
                    pattern: conf.pattern,
                    warning: conf.warning,
                    require: conf.require,
                    element: iElm
                  },
                  name = conf.name,
                  requestConf = {
                    keyName: conf.keyName,
                    method: config['apis'][conf.keyName].method
                  },
                  sendBtn = angular.element(iAttrs['phoneSend']),
                  sendTxt = sendBtn.val() || sendBtn.html();

              if(requestConf.method == 'GET')
                requestConf['params'] = {};
              else
                requestConf['data'] = {};
              formProduce.addControl(name, control);

              $scope.$watch(iAttrs['ngModel'], function(data){
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
                    messagePrompt.tooltip(control.label + '\u4E0D\u80FD\u4E3A\u7A7A !');  //不能为空
                  return;
                }
                if(control.pattern){
                  var t = control.pattern.split('/'),
                      r = new RegExp(t[1], t[t.length-1]);
                  if(!r.test(iElm.val())){
                    messagePrompt.tooltip(control.warning || (control.label + '\u4E0D\u7B26\u5408\u89C4\u8303 !'));  //不符合规范
                    return;
                  }
                }
                if(conf.isExist){
                  var checkConf = {
                    keyName: conf.isExist,
                    params: {}
                  };
                  checkConf.params[name] = iElm.val();
                  requestHandler(checkConf)
                    .success(function(data){
                      if(data[name])
                        messagePrompt.tooltip(conf.label
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
                  console.log(requestConf);
                  requestHandler(requestConf)
                    .error(function(data){
                      sendBtn.removeAttr('disabled');
                      sendBtn.val()?sendBtn.val(sendTxt): sendBtn.html(sendTxt);
                      $timeout.cancel(timer);
                    });
                  sendBtn.attr('disabled', 'disabled');
                  startTimeout(60);
                }
              });
            }
            function startTimeout(t){
              if(!t){
                sendBtn.removeAttr('disabled');
                sendBtn.val()?sendBtn.val(sendTxt): sendBtn.html(sendTxt);
                return;
              }
              var str = '\u8BF7\u7B49\u5F85' + t-- + '\u79D2';
              sendBtn.val()?sendBtn.val(str): sendBtn.html(str);
              timer = $timeout(function(){startTimeout(t)}, 1000);
            }
          });
        }
      };
    }])
    /* only check form directive
     * @date        2014-5-28
     * @author      Peach<scdzwyxst@gmail.com>
     * @see require form produce
    */
    .directive('formOnlyCheck', function(){
      return {
        restrict: 'A',
        require: '^?formProduce',
        link: function($scope, iElm, iAttrs, formProduce) {

          iElm.click(function(){
            formProduce.setOnlyFun(iAttrs['formOnlyCheck']);
            formProduce.startSubmit(true);
          });
        }
      };
    })
    /* blur directive
     * @date        2015-6-23
     * @author      Peach<scdzwyxst@gmail.com>
    */
    .directive('eventBlur', function () {
      return {
        restrict: 'A',
        link: function (scope, iElement, iAttrs) {
          iElement.bind('blur', function () {
            scope.$apply(iAttrs['eventBlur']);
          });
        }
      };
    });
});
