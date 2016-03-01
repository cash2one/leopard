define(['ionic', 'truffleService', 'truffleConfig'], function(){

  'use strict';

  return angular.module('truffleController', ['truffleService', 'truffleConfig'])
    /**
     * home controller
     * @date        2015-3-5
     * @author      Peach<scdzwyxst@gmail.com>
     */
    .controller('HomeController', ['requestHandler', '$scope','$ionicSlideBoxDelegate', function(requestHandler, $scope, $ionicSlideBoxDelegate){
      var notices = {
        banners: [],
        advance: null,
        official: null
      }

      $scope.notices = notices;

      // get trailer of projects
      // requestHandler({
      //   keyName: 'posts',
      //   params: {
      //     filter: {
      //       type: 53
      //     },
      //     limit: 3
      //   }
      // }).success(function(data){
      //   notices.advance = data;
      // });

      // get trailer of projects
      // requestHandler({
      //   keyName: 'posts',
      //   params: {
      //     filter: {
      //       type: 50
      //     },
      //     limit: 3
      //   }
      // }).success(function(data){
      //   notices.official = data;
      // });

      // get website statistic
       
      var getData = function(){
        requestHandler('statistic').success(function(data){
        $scope.statistic = data;
        });

         // get projects
        requestHandler({
          keyName: 'projects',
          params: {
            limit: 5,
            sort: 'id desc'
          }
        }).success(function(data){
          $scope.projectList = data;
        });

        requestHandler({
          keyName: 'banners',
          params: {
            sort: 'id desc'
          }
        }).success(function(data){
          $scope.notices.banners = data;
          $ionicSlideBoxDelegate.update();
        }).finally(function() {
              $scope.$broadcast('scroll.refreshComplete');
            });
      };
      getData();

      $scope.doRefresh = function(){
        getData();
      };
    
    }])
    /**
     * post list controller
     * @date        2015-3-5
     * @author      Peach<scdzwyxst@gmail.com>
     */
    .controller('PostsController', ['requestHandler', 'config', '$stateParams', '$scope'
      , function(requestHandler, config, $stateParams, $scope){
      var postData = {
        list: [],
        config: config['postTitleMapping'][$stateParams.type],
        isOver: false,
        baseUrl: '#/truffle/home/notice/' + $stateParams.type + '/'
      }

      if(!postData.config)
        return console.error('Error post type: ' + $stateParams.type + '!');

      $scope.postData = postData;

      // get post list
      $scope.loadData = function(){
        requestHandler({
          keyName: 'posts',
          params: {
            filter: {
              type: postData.config.type
            },
            offset: postData.list.length
          }
        }).success(function(data, s, header){
          if(header('Page-total') <= header('Page-current'))
            postData.isOver = true;

          postData.list = postData.list.concat(data);

          $scope.$broadcast('scroll.infiniteScrollComplete');
        });
      }

    }])
    /**
     * post detail controller
     * @date        2015-3-5
     * @author      Peach<scdzwyxst@gmail.com>
     */
    .controller('PostController', ['requestHandler', '$stateParams', '$scope', '$sce'
      , function(requestHandler, $stateParams, $scope, $sce){
      // get post detail
      requestHandler({
        keyName: 'post',
        params: {
          id: $stateParams.id
        }
      }).success(function(data){
        data.content = $sce.trustAsHtml(data.content);
        $scope.notice = data;
      });

    }])
    /**
     * project list controller
     * @date        2015-3-5
     * @author      Peach<scdzwyxst@gmail.com>
     */
    .controller('InvestmentController', ['requestHandler', '$scope', '$state'
      , function(requestHandler, $scope, $state){
        var projectData = {
          list: [],
          isOver: false,
          isStudent: $state.current.name.indexOf('student') != -1
        }

        $scope.projectData = projectData;

        // get projects
        $scope.loadData = function(){
          requestHandler({
            keyName: projectData.isStudent?'studentProjects': 'projects',
            params: {
              limit: 5,
              sort: 'id desc',
              offset: projectData.list.length
            }
          }).success(function(data, s, headers){
            if(headers('Page-total') <= headers('Page-current'))
              projectData.isOver = true;

            projectData.list = projectData.list.concat(data);

            $scope.$broadcast('scroll.infiniteScrollComplete');
          });
        }

    }])
    /**
     * project detail controller
     * @date        2015-3-5
     * @author      Peach<scdzwyxst@gmail.com>
     */
    .controller('ProjectController', ['loginService', 'messagePrompt', 'requestHandler'
      , '$stateParams', '$scope', '$ionicModal', '$ionicPopup', '$state'
      , function(loginService, messagePrompt, requestHandler, $stateParams, $scope, $ionicModal
        , $ionicPopup, $state){
        var projectData = {
              project: null,
              account: null,
              investAmount: null,
              isStudent: $state.current.name.indexOf('student') != -1
            },
            formControls = {
              conf: {},
              amount: {
                label: '投资金额',
                name: 'invest_amount',
                pattern: '/^\\d+(\\.\\d{1,2})?$/',
                require: true
              },
              models: {
                amount: null
              }
            };

        $scope.projectData = projectData;
        $scope.formControls = formControls;

        // get project data
        var getProjectData = function(){
            requestHandler({
              keyName: projectData.isStudent?'studentProject': 'project',
              params: {
                id: $stateParams.id
              }
            }).success(function(data){
              projectData.project = data;
            });
        }
        getProjectData();

        var getAccountData = function(){
          requestHandler('account').success(function(data){
            projectData.account = data;
          }).finally(function() {
              $scope.$broadcast('scroll.refreshComplete');
          });
        }
        getAccountData();
        $scope.doRefresh = function(){
          getAccountData();
          getProjectData();
        };
        // init modal
        $ionicModal.fromTemplateUrl('/views/project_record.html', {
          scope: $scope
        }).then(function(modal) {
          $scope.recordModal = modal;
        });

        // destroy modal
        $scope.$on('$destroy', function(){
          $scope.recordModal.remove();
        })

        $scope.lendProject = function(isDeposit){
          $ionicPopup.show({
            title: '投标确认',
            subTitle: isDeposit?'不可以得到回款续投奖励': '可以得到回款续投奖励',
            template: '\
              <input type="password" placeholder="请输入交易密码"\
               ng-model="formControls.models.tradePassword" />\
               <br />\
              <input type="password" placeholder="请输入定向密码"\
               ng-model="formControls.models.password" ng-if="projectData.project.has_password"/>\
              ',
            scope: $scope,
            buttons: [
              { text: '取消' },
              {
                text: '<b>投标</b>',
                type: 'button-positive',
                onTap: function(e){
                  if (!$scope.formControls.models.tradePassword) {
                    messagePrompt.tooltip('请先输入交易密码！');
                    e.preventDefault();
                  }
                  else {
                    return $scope.formControls.models;
                  }
                }
              }
            ]
          }).then(function(models){
            if(!models.tradePassword)
              return;
            requestHandler({
              keyName: 'lend',
              params: {
                id: projectData.project.id
              },
              data: {
                amount: formControls.models.amount,
                trade_password: models.tradePassword,
                password: models.password,
                capital_deduct_order: isDeposit?0: 1
              }
            }).success(function(data){
              formControls.models.amount = null;
              getProjectData();
              getAccountData()
            });

            formControls.models.tradePassword = null;
            formControls.models.password = null;
          });
        }

        $scope.login = loginService.openModal;
    }])
    /**
     * student apply controller
     * @date        2015-3-31
     * @author      Peach<scdzwyxst@gmail.com>
     */
    .controller('StudentApplyController', ['$scope', function ($scope) {
      var formControls = {
          conf: {
            keyName: 'lendStudent'
          },
          amount: {
            label: '借款额度',
            name: 'amount',
            pattern: '/^\\d+000$/',
            min: 1000,
            max: 999999999,
            warning: '借款金额必须为1000的倍数',
            require: true
          },
          periods: {
            label: '借款期限',
            name: 'term',
            pattern: '/^\\d+$/',
            min: 1,
            require: true
          },
          realname: {
            label: '姓名',
            name: 'name',
            require: true
          },
          grade: {
            label: '现读年级',
            name: 'grade',
            require: true
          },
          schoolName: {
            label: '学校名称',
            name: 'school',
            require: true
          },
          idcard: {
            label: '身份证号码',
            name: 'idcard',
            pattern: '/^[1-9]\\d{5}[1-9]\\d{3}((0\\d)|(1[0-2]))(([0|1|2]\\d)|3[0-1])[\\dX]{4}$/',
            require: true
          },
          mobile: {
            label: '手机号码',
            name: 'phone',
            pattern: '/^[1][1-9][\\d]{9}$/',
            require: true
          },
          models: {
              periods: 6
          }
        }

        $scope.formControls = formControls;

        formControls.conf['success'] = function(data){
            $scope.formControls.models = {
                periods: 6
            };
        }

        formControls.conf['error'] = function(data){
            console.log($scope.formControls.models)
        }
    }])
    /**
     * account controller
     * @date        2015-3-6
     * @author      Peach<scdzwyxst@gmail.com>
     */
    .controller('AccountController', ['loginService', 'requestHandler', '$scope'
      , function(loginService, requestHandler, $scope){
      var accountData = {
        account: null
      }

      $scope.accountData = accountData;

      var getData = function(){
         // get account informations
        requestHandler('account').success(function(data){
          accountData.account = data;
        }).finally(function() {
              $scope.$broadcast('scroll.refreshComplete');
            });
      };
      getData();
     
      $scope.doRefresh = function(){
        getData();
      };

      $scope.logout = loginService.logout;
    }])
    /**
     * password controller
     * @date        2015-3-6
     * @author      Peach<scdzwyxst@gmail.com>
     */
    .controller('PasswordController', ['requestHandler', '$scope', function(requestHandler, $scope){
      var formControls = {
        conf: {
          keyName: 'password'
        },
        originalPassword: {
          label: '新密码',
          name: 'oldpassword',
          require: true
        },
        newPassword: {
          label: '新密码',
          name: 'newpassword',
          pattern: '/^[a-z][a-z0-9]{7,31}$/i',
          warning: '登录密码应由8-32位数字、英文组成且首位必须为字母',
          require: true
        },
        confirmPassword: {
          label: '重复密码',
          name: 'repassword',
          seemAs: 'newpassword',
          require: true
        },
        models: {
          originalPassword: null,
          newPassword: null,
          confirmPassword: null
        }
      }

      formControls.conf['success'] = function(data){
            $scope.formControls.models = {
                originalPassword: null,
                newPassword: null,
                confirmPassword: null
            };
        }

      $scope.formControls = formControls;
    }])
    /**
     * bankcard controller
     * @date        2015-3-6
     * @author      Peach<scdzwyxst@gmail.com>
     */
    .controller('BankcardController', ['messagePrompt', 'requestHandler', '$scope', '$ionicModal', '$ionicPopup'
      , function(messagePrompt, requestHandler, $scope, $ionicModal, $ionicPopup){
      var bankcardData = {
            list: null
          },
          depositBankcardData = {
             list: null
          },
          formControls = {
            conf: {
              keyName: 'bankcard',
              method: 'POST'
            },
            number: {
              label: '银行卡号',
              name: 'card',
              pattern: '/^[0-9]{16,19}$/i',
              require: true
            },
            bank: {
              label: '银行名称',
              name: 'name',
              require: true
            },
            opened: {
              label: '开户行',
              name: 'branch',
              require: true
            },
            models: {
              number: null,
              bank: null,
              opened: null
            }
          };

      formControls.conf['success'] = function(data){
        $scope.addModal.hide();
        bankcardData.list.unshift({
          bank: data.bank,
          card: data.card,
          id: data.id
        });
      }

      $scope.formControls = formControls;
      $scope.bankcardData = bankcardData;
      $scope.depositBankcardData = depositBankcardData;

      // get bankcards
      requestHandler('bankcard').success(function(data){
        bankcardData.list = data;
      });

      // get deposit bankcards
      requestHandler({keyName: 'depositBankcard',
            params: {
              platform_type: 'YintongAuthentication'
            }
          }).success(function(data){
        depositBankcardData.list = data;
      });

      // init add bankcar modal
      $ionicModal.fromTemplateUrl('/views/account/bankcard_add.html', {
          scope: $scope
        })
        .then(function(modal){
          $scope.addModal = modal;
        });

      // destroy modal
      $scope.$on('$destroy', function(){
        $scope.addModal.remove();
      })

      // remove bankcard
      $scope.removeBankcard = function(id, platform, $index){
        $ionicPopup.show({
          title: '删除银行卡',
          template: '\
            输入交易密码方可删除银行卡，删除后将不可恢复！\
            <input type="password" placeholder="请输入交易密码"\
             ng-model="formControls.models.tradePassword" />\
            ',
          scope: $scope,
          buttons: [
            {
              text: '<b>删除</b>',
              type: 'button-assertive',
              onTap: function(e){
                if (!$scope.formControls.models.tradePassword) {
                  messagePrompt.tooltip('请先输入交易密码！');
                  e.preventDefault();
                } else {
                  return $scope.formControls.models.tradePassword;
                }
              }
            },
            { text: '取消' }
          ]
        }).then(function(password){
          if(!password)
            return;
          requestHandler({
            keyName: 'removeBankcard',
            params: {
              id: id,
              trade_password: password,
              platform_type: platform
            }
          }).success(function(){
            if (!platform){
              bankcardData.list.splice($index, 1);
            }else{
              depositBankcardData.list.splice($index, 1)
            }
            
          });

          formControls.models.tradePassword = null;
        });
      }

    }])
    /**
     * student_apply controller
     * @date        2015-04-13
     * @author      NSDont<haodewanan@gmail.com>
     */
    .controller('StudentApplyLogsController', ['requestHandler', '$state', '$scope'
      , function(requestHandler, $state, $scope){
        var ApplyData = {
              list: [],
              isOver: false
        };

        $scope.ApplyData = ApplyData;

        // load Student Apply from server
        $scope.loadData = function(){
          requestHandler({
            keyName: 'lendStudents',
            params: {
              limit: 10,
              sort: 'id desc',
              offset: ApplyData.list.length
            }
          }).success(function(data, s, headers){
            if(headers('Page-total') <= headers('Page-current'))
              ApplyData.isOver = true;

            ApplyData.list = ApplyData.list.concat(data);

            $scope.$broadcast('scroll.infiniteScrollComplete');
          });
        }

    }])
    /**
     * logs controller
     * @date        2015-3-6
     * @author      Peach<scdzwyxst@gmail.com>
     */
    .controller('LogsController', ['requestHandler', '$state', '$scope'
      , function(requestHandler, $state, $scope){
        var logsData = {
              list: [],
              isOver: false
            },
            requestKey = $state.current.url.substring(1) + 'Logs'

        $scope.logsData = logsData;

        // load logs from server
        $scope.loadData = function(){
          requestHandler({
            keyName: requestKey,
            params: {
              limit: 10,
              sort: 'id desc',
              offset: logsData.list.length
            }
          }).success(function(data, s, headers){
            if(headers('Page-total') <= headers('Page-current'))
              logsData.isOver = true;

            var i = 0;
            for (i = 0; i < data.length; i++) {
                if(data.description)
                    data[i] = data[i].description.replace(/<\/?[^>]*>/g,'');
            }

            logsData.list = logsData.list.concat(data);

            $scope.$broadcast('scroll.infiniteScrollComplete');
          });
        }

    }])
    /**
     * red packet controller
     * @date        2015-3-6
     * @author      Peach<scdzwyxst@gmail.com>
     */
    .controller('RedPacketController', ['messagePrompt', 'requestHandler', '$scope'
      , function(messagePrompt, requestHandler, $scope){
      var redPacketData = {
        list: [],
        isOver: false
      }

      $scope.redPacketData = redPacketData;

      // load logs from server
      $scope.loadData = function(){
        requestHandler({
          keyName: 'redPackets',
          params: {
            limit: 10,
            offset: redPacketData.list.length
          }
        }).success(function(data, s, headers){
          if(headers('Page-total') <= headers('Page-current'))
            redPacketData.isOver = true;

          redPacketData.list = redPacketData.list.concat(data);

          $scope.$broadcast('scroll.infiniteScrollComplete');
        });
      }

      // use red packet
      $scope.useRedPacket = function(redPacket, $index){
        if(!redPacket.is_available)
          return messagePrompt.tooltip('此红包需激活后才能使用');
        if(redPacket.is_use || redPacket.is_expiry)
          return;

        requestHandler({
          keyName: 'redPacket',
          params: {
            id: redPacket.id
          }
        }).success(function(data){
          $scope.redPacketData.list[$index].is_use = true;
        });
      };
    }])
    /**
     * automatic controller
     * @date        2015-3-6
     * @author      Peach<scdzwyxst@gmail.com>
     */
    .controller('AutomaticController', ['requestHandler', '$scope'
      , function(requestHandler, $scope){
      var formControls = {
        conf: {
          keyName: 'automatic',
          method: 'PUT'
        },
        isOpen: {
          label: '是否启用',
          name: 'is_open'
        },
        maxAmount: {
          label: '最大投资额',
          name: 'max_amount',
          pattern: '/^\\d+(\\.\\d{1,2})?$/',
          require: true
        },
        minAmount: {
          label: '最小投资额',
          name: 'min_amount',
          pattern: '/^\\d+(\\.\\d{1,2})?$/',
          require: true
        },
        maxRate: {
          label: '最大利率',
          name: 'max_rate',
          pattern: '/^(?!0+(?:\\.0+)?$)(?:[1-9]\\d*|0)(?:\\.\\d{1})?$/',
          min: 0.1,
          max: 24.0,
          require: true
        },
        minRate: {
          label: '最小利率',
          name: 'min_rate',
          pattern: '/^(?!0+(?:\\.0+)?$)(?:[1-9]\\d*|0)(?:\\.\\d{1})?$/',
          min: 0.1,
          max: 24.0,
          require: true
        },
        maxPeriods: {
            label: '最大期数',
            name: 'max_periods',
            pattern: '/^\\d+$/',
            min: 1,
            require: true
        },
        minPeriods: {
          label: '最小期数',
          name: 'min_periods',
          pattern: '/^\\d+$/',
          min: 1,
          require: true
        },
        reserveAmount: {
          label: '账户预留金额',
          name: 'reserve_amount',
          require: true
        },
        tradePass: {
          label: '交易密码',
          name: 'trade_password',
          require: true
        },
        models: {}
      }

      formControls.conf['success'] = function(data){
          formControls.models.tradePass = null;
      }

      $scope.formControls = formControls;

      // get settings
      requestHandler('automatic').success(function(data){
        formControls.models = data;
        formControls.models.is_open;
        $scope.togglePower();
      });

      //set a function to change the auto invest
      $scope.togglePower = function(){
        for(var i in formControls)
          if(i != 'conf' && i != 'models' && i != 'isOpen' && i != 'tradePass'){
            formControls[i].require = formControls.models.is_open;
          }
      }
    }])
    /**
     * automatic controller
     * @date        2015-6-23
     * @author      Peach<scdzwyxst@gmail.com>
     */
    .controller('RegisterController', ['requestHandler', '$scope', function (requestHandler, $scope) {
      var current_date = (new Date()).getTime(),
        formControls = {
        conf: {
          keyName: 'register'
        },
        inviteCode: {
          label: '邀请人',
          name: 'friend_invitation'
        },
        username: {
          label: '用户名',
          name: 'username',
          pattern: '/^[a-zA-Z0-9\\u4E00-\\u9FA5]{3,32}$/',
          warning: '用户名应由3-32位数字、英文或中文组成 !',
          isExist: 'checkRegisterExist',
          require: true
        },
        password: {
          label: '密码',
          name: 'password',
          pattern: '/^[a-z][a-z0-9]{7,31}$/i',
          warning: '登录密码应由8-32位数字、英文组成且首位必须为字母',
          require: true
        },
        rePassword: {
          label: '重复密码',
          name: 'repassword',
          seemAs: 'password',
          require: true
        },
        phone: {
          label: '手机号码',
          name: 'phone',
          pattern: '/^[1][1-9][\\d]{9}$/',
          keyName: 'registerCode',
          require: true
        },
        phoneCode: {
          label: '短信验证码',
          name: 'phone_code',
          require: true
        },
        models: {
          username: null,
          password: null,
          rePassword: null,
          phone: null,
          phoneCode: null,
          inviteCode: null,
          inviteUser: null,
          current_date: current_date,
        }
      };

      $scope.formControls = formControls;

      $scope.reload_vcode = function reload_vcode(){
        var current_date = (new Date()).getTime();
        formControls.models.current_date = current_date;
      }

      $scope.getInviteUser = function () {
        if(formControls.models.inviteCode){
          requestHandler({
            keyName: 'getInvitedUser',
            params: {
              invite_code: formControls.models.inviteCode
            }
          }).success(function (data) {
            formControls.models.inviteUser = data.username;
          });
        }
      }
    }])
    /**
     * RechargeController controller
     * @date        2015-12-15
     * @author      Xxguo<xxguo81527@foxmail.com>
     */
    .controller('RechargeController', ['requestHandler', '$ionicModal', '$scope'
      , function(requestHandler, $ionicModal, $scope){
      var formControls = {
        conf: {
          keyName: 'recharge'
        },
        amount: {
          label: '金额',
          name: 'amount',
          pattern: '/^\\d+(\\.\\d{1,2})?$/',
          min: 0,
          require: true
        },
        platform: {
          label: '充值平台',
          name: 'platform',
          require: true
        },
        comment: {
          label: '流水号',
          name: 'comment'
        },
        bankcard: {
          label: '银行卡',
          name: 'bankcard_id',
          require: true
        },
        models: {
          amount: null,
          comment: null,
          bankcard: null,
          platform: null
        }
      },
      depositData = {
        platformList: [],
        platform: null
      },
      rechargeForm = {
        models: {
          action: null,
          value: null
        }
      };

      formControls.conf['success'] = function(data){
          formControls.models.amount = null;
          formControls.models.comment = null;
          if (data.action){
            rechargeForm.models.action = data.action;
            rechargeForm.models.value = data.req_data
            $scope.rechargeModal.show();
          }
      }

      $scope.formControls = formControls;
      $scope.depositData = depositData;
      $scope.rechargeForm =rechargeForm;

      // get settings
      requestHandler('getPaymentPlatform').success(function(data){
        depositData.platformList = data;
        depositData.platform = data[0];
      });

      // get bankcards
      requestHandler('bankcard').success(function(data){
        formControls.bankcards = data;
      });

      // set deposit
      $ionicModal.fromTemplateUrl('/views/account/recharge_ready_form.html', {
        scope: $scope
      })
      .then(function(modal){
        $scope.rechargeModal = modal;
      });

      // destroy modal
      $scope.$on('$destroy', function(){
        $scope.rechargeModal.remove();
      })

    }])
    /**
     * RechargeController controller
     * @date        2015-12-15
     * @author      Xxguo<xxguo81527@foxmail.com>
     */
    .controller('WithdrawController', ['requestHandler', 'messagePrompt', '$scope'
      , function(requestHandler, messagePrompt,  $scope){
      var formControls = {
        conf: {
            keyName: 'createWithdraw'
        },
        amount: {
            label: '提现金额',
            name: 'amount',
            pattern: '/^\\d+(\\.\\d{1,2})?$/',
            min: 100,
            require: true
        },
        tradePass: {
            label: '交易密码',
            name: 'trade_password',
            require: true
        },
        phoneCode: {
            label: '短信验证码',
            name: 'phone_code',
            keyName: 'withdrawCode',
            require: true
        },
        bankcard: {
            label: '银行卡',
            name: 'bankcard_id',
            require: true
        },
        models: {
            amount: null,
            tradePass: null,
            phoneCode: null,
            bankcard: null,
            amountType: 0
        }
      },
      bankcardData = {
        bankcardList:null,
        bankcard: null
      },
      accountData = {};

      formControls.conf['success'] = function(data){
          formControls.models.amount = null;
          formControls.models.tradePass = null;
          formControls.models.tradePass = null;
      }

      requestHandler('account').success(function(data){
          accountData.account = data;
        });

      $scope.formControls = formControls;
      $scope.accountData = accountData;
      $scope.bankcardData = bankcardData;

     // get bankcards
      requestHandler('bankcard').success(function(data){
        bankcardData.bankcardList = data;
      });


    }])

    ;
});
