define(['ionic'], function(){

  'use strict';

  return angular.module('truffleConfig', [])
    .constant('config', {

      /**
       * api configration
       * @date        2015-3-3
       * @author      Peach<scdzwyxst@gmail.com>
       */
      apis: {
        baseUrl: 'http://www.zhongbaodai.com/service',
        banners: '/board/banners',
        posts: '/board/post',
        post: '/board/post/:id',
        statistic: '/lending/trade_stat',
        projects: '/lending/public_project',
        project: '/lending/public_project/:id',
        studentProjects: '/lending/finproject',
        studentProject: '/lending/finproject/:id',
        lendStudent:
        {
          url: '/lending/finmobileapplication',
          method: 'POST'
        },
        lendStudents: '/lending/finmobileapplication',
        login: {
          url: '/auth/session',
          method: 'POST'
        },
        register: {
          url: '/auth/user',
          method: 'POST'
        },
        account: '/auth/user',
        password: {
          url: '/auth/password',
          method: 'PUT'
        },
        bankcard: '/account/bankcard',
        depositBankcard: '/account/desposit_bankcard/:platform_type',
        removeBankcard: {
          url: '/account/bankcard/:id',
          method: 'DELETE'
        },
        investmentLogs: '/lending/investment',
        lend: {
          url: '/lending/investment/:id',
          method: 'POST'
        },
        lendingLogs: '/lending/plans',
        depositLogs: '/account/deposit',
        withdrawLogs: '/account/withdraw',
        fundLogs: '/account/log',
        redPackets: '/account/red_packet',
        redPacket: {
          url: '/account/red_packet/:id',
          method: 'PUT'
        },
        automatic: '/lending/autoinvest',
        getPaymentPlatform: '/account/deposit_platform/mobile',
        recharge: {
          url: '/account/deposit/mobile',
          method: 'POST'
        },
        createWithdraw: {
          url: '/account/withdraw',
          method: 'POST'
        },

        // 远端检查接口
        checkRegisterExist: {
          url: '/auth/duplicated_user',
          method: 'GET'
        },
        registerCode: {
          url: '/auth/register_phone_code/:ver_code/',
          method: 'GET'
        },
        withdrawCode: {
            url: '/auth/phone_code/withdraw',
            method: 'GET'
        },
        getInvitedUser: {
            url: '/auth/friend_invitation/:invite_code',
            method: 'GET'
        }
      },

      /**
       * post config mapping
       * @date        2015-3-4
       * @author      Peach<scdzwyxst@gmail.com>
       */
      postTitleMapping: {
        'advance': {
          title: '发标预告',
          type: 53
        },
        'official': {
          title: '网站公告',
          type: 50
        }
      },


      /* status config
      ** @date        2014-5-18
      ** @author      Peach<scdzwyxst@gmail.com>
      */
      statusConfig: {
        'apply': {
          '100': '担保机构审核中',
          '199': '担保机构审核失败',
          '200': '风控审核中',
          '299': '风控审核失败',
          '300': '审核通过'
        },
        'invest': {
          '100': '投资未生效',
          '200': '投资生效',
          '299': '投资失败',
          '300': '转让中',
          '400': '转让完成',
          '500': '提前全额还款'
        },
        'repay': {
          '100': '未生效',
          '200': '还款中',
          '300': '还款成功',
          '399': '还款失败',
          '400': '提前全额还款',
          '500': '已转让'
        },
        'deposit': {
          '100': '处理中',
          '300': '充值成功',
          '399': '充值失败'
        },
        'withdraw': {
          '100': '处理中',
          '200': '开始提现',
          '300': '提现成功',
          '399': '提现失败'
        },
        'lend': {
          '100': '自动投资中',
          '200': '投资中',
          '300': '满标处理中',
          '400': '还款中',
          '500': '项目完结',
          '599': '项目流标',
          '600': '提前全额还款'
        },
        'plan': {
          '100': '还款中',
          '200': '已还款',
          '299': '还款失败',
        },
        'log': {
          '100': '处理中',
          '200': '处理开始',
          '300': '处理成功',
          '399': '处理失败'
        },
        'project_category': {
          '100': '抵押标',
          '200': '信用标',
          '300': '担保标',
          '400': '秒标',
        },
        'student': {
          '100': '等待审核',
          '200': '借款成功',
          '299': '借款失败'
        },
        'student-plan': {
          '100': '还款中',
          '200': '还款成功',
          '299': '还款逾期'
        },
        'card_type': {
          '2': '储蓄卡',
          '3': '信用卡'
        },
        'vip-status': {
          '0': '普通',
          '1': 'VIP',
          '2': 'SVIP',
          '3': '特级'
        }
      },
    });
})
