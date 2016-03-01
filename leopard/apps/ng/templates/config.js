define(['app'], function (app) {

    'use strict';

    app.constant('config', {
        /*Name: Top navbar configs
         *Author: Peach
         *Time: 2014-5-5
        */
        navbar: [
            {
                name: '首　页',  //navbar title
                pattern: '/',  //location match
                link: '/',  //navbar href
                childrens: []  //second navs, fomartting: {name: 'ABC', link: '/ABC'}
            },
            {
                name: '我要出借',
                pattern: '/invest.*',
                link: '/invest',
                childrens: []
            },
            {
                name: '我要借款',
                pattern: '/lend.*',
                link: '/lend',
                childrens: []
            },
            {
                name: '账户中心',
                pattern: '/account.*',
                link: '/account/dashboard',
                childrens: []
            },
            {
                name: '帮助中心',
                pattern: '/post/help.*',
                link: '/post/help/zhongbao',
                childrens: []
            }
        ],
        /*Name: account url config
         *Author: Peach
         *Time: 2014-5-8
        */
        accountUrl: [
            {
                name: '账户概览',
                id: 'dashboard',
                templateUrl: '/views/account/home.html'
            },
            {
                id: 'ranking',
                name: '排行榜',
                templateUrl: '/views/account/ranking.html'
            },
            {
                id: 'deposit-new',
                name: '充值',
                templateUrl: '/views/account/deposit_new.html'
            },
            {
                id: 'withdraw-new',
                name: '提现',
                templateUrl: '/views/account/withdraw_new.html'
            },
            {
                name: '我的账户',
                id: 'management',
                links: [
                    {
                        id: 'profile',
                        name: '资料修改',
                        link: '/profile',
                        templateUrl: '/views/account/profile.html',
                        isInvestor: true
                    },
                    {
                        id: 'bankcard',
                        name: '银行卡管理',
                        link: '/bankcard',
                        templateUrl: '/views/account/bankcard.html',
                        isInvestor: true
                    },
                    {
                        id: 'red-packet',
                        name: '红包管理',
                        link: '/red-packet',
                        templateUrl: '/views/account/red_packet.html',
                        isInvestor: true
                    },
                    {
                        id: 'gift-point',
                        name: '宝币管理',
                        link: '/gift-point',
                        templateUrl: '/views/account/gift_point.html',
                        isInvestor: true
                    },
                    {
                        id: 'invitation',
                        name: '好友邀请',
                        link: '/invitation',
                        templateUrl: '/views/account/invitation.html',
                        isInvestor: true
                    },
                    {
                        id: 'vip',
                        name: 'VIP服务',
                        link: '/vip',
                        templateUrl: '/views/account/vip.html',
                        isInvestor: true
                    },
                    {
                        id: 'inbox',
                        name: '消息中心',
                        link: '/inbox',
                        templateUrl: '/views/account/inbox.html',
                        isInvestor: true
                    },
                    {
                        id: 'automatic',
                        name: '自动投标设置',
                        link: '/automatic',
                        templateUrl: '/views/account/automatic.html',
                        isNew: true,
                        isInvestor: true
                    }
                ]
            },
            {
                name: '资金管理',
                id: 'funding',
                links: [
                    {
                        id: 'investment',
                        name: '投资记录',
                        link: '/investment',
                        templateUrl: '/views/account/investment.html',
                        isInvestor: true
                    },
                    {
                        id: 'lending',
                        name: '待收记录',
                        link: '/lending',
                        templateUrl: '/views/account/lending.html',
                        isInvestor: true
                    },
                    {
                        id: 'deposit',
                        name: '充值记录',
                        link: '/deposit',
                        templateUrl: '/views/account/deposit.html',
                        isInvestor: true
                    },
                    {
                        id: 'withdraw',
                        name: '提现记录',
                        link: '/withdraw',
                        templateUrl: '/views/account/withdraw.html',
                        isInvestor: true
                    },
                    {
                        id: 'log',
                        name: '资金记录',
                        link: '/log',
                        templateUrl: '/views/account/log.html',
                        isInvestor: true
                    },
                    {
                        id: 'apply',
                        name: '申请书列表',
                        link: '/apply',
                        templateUrl: '/views/account/apply.html',
                    },
                    {
                        id: 'borrowing',
                        name: '借款记录',
                        link: '/borrowing',
                        templateUrl: '/views/account/borrowing.html',
                    },
                    {
                        id: 'repayment',
                        name: '还款记录',
                        link: '/repayment',
                        templateUrl: '/views/account/repayment.html',
                    }
                ]
            },
            {
                name: '学仕贷管理',
                id: 'student',
                links: [
                    {
                        id: 'student-apply',
                        name: '学仕贷申请书列表',
                        link: '/student-apply',
                        templateUrl: '/views/account/student_apply.html',
                    },
                    {
                        id: 'student-repayment',
                        name: '学仕贷申请书还款记录',
                        link: '/student-repayment',
                        templateUrl: '/views/account/student_repayment.html',
                    },
                    {
                        id: 'finrepayment',
                        name: '学仕贷还款记录',
                        link: '/finrepayment',
                        templateUrl: '/views/account/finrepayment.html',
                    }
				]
			}
        ],
        /*Name: friend links configs
         *Author: Peach
         *Time: 2014-5-12
        */
        friendLinks: [
            {% for i in FRIENDLINKS%}
                {
                    name: '{{ i.name }}',
                    link: '{{ i.link }}'
                },
            {% endfor %}
        ],
        /*Name: partners configs
         *Author: NSDont
         *Time: 2014-6-26
        */
        partners: [
            {% for i in PARTNERS%}
                {
                    name: '{{ i.name }}',
                    link: '{{ i.link }}',
                    img: '{{ i.img }}'
                },
            {% endfor %}
        ],

        /*Name: bottom navbar configs
         *Author: Peach
         *Time: 2014-5-12
        */
        bottomNavbar: [
            {
                name: '关于我们',
                link: '/#!/post/about/info'
            },
            {
                name: '安全保障',
                link: '/#!/post/security/introduction'
            },
            {
                name: '法律法规',
                link: '/#!/post/law/introduction'
            },
            {
                name: '帮助中心',
                link: '/#!/post/help/zhongbao'
            },
            {
                name: '网站动态',
                link: '/#!/post/trend/notice'
            }
        ],
        /*Name: platform configs
         *Author: Peach
         *Time: 2014-5-12
        */
        platformConfig: {
            name: '{{ PROJECT.CORPORATION }}',
            fullName: '{{ PROJECT.CORPORATION_FULLNAME }}',
            phone: '{{ PROJECT.CORPORATION_TEL }}',
            ICP: '{{ PROJECT.CORPORATION_ICP }}',
            domain: '{{ PROJECT.HOST }}',
            address: '{{ PROJECT.CORPORATION_ADDRESS }}',
            postCode: '{{ PROJECT.CORPORATION_POSTCODE }}',
            city: '{{ PROJECT.CORPORATION_CITY }}',
            tradePass: {
                invest: {{ TRADE_PASSWORD_ENABLE }}
            },
            bankcardNumber: 6
        },
        /*Name: banner configs
         *Author: Peach
         *Time: 2014-5-15
        */
        bannerConfig: {
            changeTime: 5000,  //how long time to change the image (ms)
            loadTime: 8000,  //set the limit time for load images (ms)
            list: [  //banner images
            {% for banner in BANNERS%}
                {
                    src: '{{ banner.src }}',
                    link: '{{ banner.link }}'
                },
            {% endfor %}
            ]
        },
        /*Name: Morris.js configs
         *Author: Peach
         *Time: 2014-5-15
        */
        morrisConfig: {
            colors: ['#95bbd7', '#4084b8', '#0b62a4', '#014374']
        },
        /*Name: flash zeroClipBoard configs
         *Author: Peach
         *Time: 2014-5-15
        */
        zeroClipConfig: {
            swfPath: '/bower_components/zeroclipboard/ZeroClipboard.swf', //set the path of swf
            forceHandCursor: true,  //forcibly set the hand cursor ("pointer")
            zIndex: 999999999
        },
        /*Name: all resource config
         *Author: Peach
         *Time: 2014-5-17
        */
        resConfig: {
            //entrance interface
            register: {
                url: '/service/auth/user',
                method: 'POST'
            },
            getInvitedUser: {
                url: '/service/auth/friend_invitation/:invite_code',
                method: 'GET'
            },
            getInvitedUserByCode: {
                url: '/service/auth/invite_code/:invite_code',
                method: 'GET'
            },
            checkRegisterExist: {
                url: '/service/auth/duplicated_user',
                method: 'GET'
            },
            login: {
                url: '/service/auth/session',
                method: 'POST'
            },
            checkLogin: {
                url: '/service/auth/session',
                method: 'GET'
            },
            logout: {
                url: '/service/auth/session',
                method: 'DELETE'
            },
            setBackPass: {
                url: 'service/auth/resetter_password',
                method: 'PUT'
            },
            getRank: {
                url: '/service/lending/rank',
                method: 'GET'
            },
            //user interface
            getUser: {
                url: '/service/auth/user',
                method: 'GET'
            },
            getPlatformInfo: {
                url: '/service/lending/trade_stat',
                method: 'GET'
            },
            createWithdraw: {
                url: '/service/account/withdraw',
                method: 'POST'
            },
            getPaymentPlatform: {
                url: '/service/account/deposit_platform',
                method: 'GET'
            },
            createDeposit: {
                url: '/service/account/deposit',
                method: 'POST'
            },
            getPosts: {
                url: '/service/board/post',
                method: 'GET'
            },
            getPost: {
                url: '/service/board/post/:post_id',
                method: 'GET'
            },
            getInvestment: {
                url: '/service/lending/investment',
                method: 'GET'
            },
            getAccountInvestment: {
                url: '/service/lending/account_investment',
                method: 'GET'
            },
            getAccountInvestmentDetail: {
                url: '/service/lending/account_investment/:investment_id',
                method: 'GET'
            },
            getPlans: {
                url: '/service/lending/plans',
                method: 'GET'
            },
            getBorrowing: {
                url: '/service/lending/project',
                method: 'GET'
            },
            getRepayments: {
                url: '/service/lending/repayment',
                method: 'GET'
            },
            getFinRepayments: {
                url: '/service/lending/finrepayment',
                method: 'GET'
            },
            getFinRepaymentPlans: {
                url: '/service/lending/finrepayment/:project_id',
                method: 'GET'
            },
            getStudentRepayments: {
                url: '/service/lending/finapplication/:id/plan',
                method: 'GET'
            },
            repayProject: {
                url: '/service/lending/project/:project_id/prepayment_all',
                method: 'PUT'
            },
            repayRepayment: {
                url: '/service/lending/repayment/:project_id/:repayment_id',
                method: 'PUT'
            },
            repayFinRepaymentPlan: {
                url: '/service/lending/finrepayment/:project_id/:repayment_id',
                method: 'PUT'
            },
            repayStudentRepayment: {
                url: '/service/lending/finapplication/:project_id/plan/:plan_id',
                method: 'PUT'
            },
            getApply: {
                url: '/service/lending/application',
                method: 'GET'
            },
            getStudentApply: {
                url: '/service/lending/finapplication',
                method: 'GET'
            },
            getDeposit: {
                url: '/service/account/deposit',
                method: 'GET'
            },
            getWithdraw: {
                url: '/service/account/withdraw',
                method: 'GET'
            },
            cancelWithdraw: {
                url: '/service/account/withdraw/:withdraw_id',
                method: 'DELETE'
            },
            getLog: {
                url: '/service/account/log',
                method: 'GET'
            },
            getGiftPoint: {
                url: '/service/account/giftpoint',
                method: 'GET'
            },
            getBankcard: {
                url: '/service/account/bankcard',
                method: 'GET'
            },
            createBankcard: {
                url: '/service/account/bankcard',
                method: 'POST'
            },
            removeBankcard: {
                url: '/service/account/bankcard/:bankcard_id',
                method: 'DELETE'
            },
            getRedPacket: {
                url: '/service/account/red_packet',
                method: 'GET'
            },
            getTenderRedPacket: {
                url: '/service/account/tender_red_packet/:tender_amount',
                method: 'GET'
            },
            useRedPacket: {
                url: '/service/account/red_packet/:packet_id',
                method: 'PUT'
            },
            useCodeRedPacket: {
                url: '/service/account/code_red_packet',
                method: 'PUT'
            },
            useAllPacket: {
                url: '/service/account/red_packet_full',
                method: 'PUT'
            },
            getProfile: {
                url: '/service/auth/user/profile',
                method: 'GET'
            },
            changeProfile: {
                url: '/service/auth/user/profile',
                method: 'PUT'
            },
            changePhone: {
                url: '/service/auth/change_phone',
                method: 'PUT'
            },
            changeEmail: {
                url: '/service/authentication/2',
                method: 'PUT'
            },
            setEmail: {
                url: '/service/authentication/2',
                method: 'POST'
            },
            getEmail: {
                url: '/service/authentication/2',
                method: 'GET'
            },
            changePassword: {
                url: '/service/auth/password',
                method: 'PUT'
            },
            setTradePass: {
                url: '/service/auth/trade_password',
                method: 'POST'
            },
            changeTradePass: {
                url: '/service/auth/trade_password',
                method: 'PUT'
            },
            getRealname: {
                url: '/service/authentication/1',
                method: 'GET'
            },
            setRealname: {
                url: '/service/authentication/1',
                method: 'POST'
            },
            changeRealname: {
                url: '/service/authentication/1',
                method: 'PUT'
            },
            setAutoInvest: {
                url: '/service/lending/autoinvest',
                method: 'PUT'
            },
            getAutoInvest: {
                url: '/service/lending/autoinvest',
                method: 'GET'
            },
            getVipInfo: {
                url: '/service/auth/vip',
                method: 'GET'
            },
            setVip: {
                url: '/service/auth/vip',
                method: 'PUT'
            },
            getCustomerService: {
                url: '/service/auth/vip_server',
                method: 'GET'
            },
            setCustomerService: {
                url: '/service/auth/vip_server',
                method: 'PUT'
            },
            getMessages: {
                url: '/service/social/inbox',
                method: 'GET'
            },
            readMessage: {
                url: '/service/social/inbox/:message_id',
                method: 'PUT'
            },
            removeMessage: {
                url: '/service/social/inbox/:message_id',
                method: 'DELETE'
            },
            removeAllMessages: {
                url: '/service/social/inbox',
                method: 'DELETE'
            },
            getContract: {
                url: '/service/lending/investment/:investment_id/contract',
                method: 'GET'
            },
            getTransferContract: {
                url: '/service/lending/investment/:investment_id/transfer_contract',
                method: 'GET'
            },
            getAssigneeContract: {
                url: '/service/lending/investment/:investment_id/assignee_contract',
                method: 'GET'
            },
            //assignment interface
            getAssignmentList: {
                url: '/service/lending/investment_transferring',
                method: 'GET'
            },
            getAssignment: {
                url: '/service/lending/investment_transferring/:investment_id',
                method: 'GET'
            },
            buyAssignment: {
                url: '/service/lending/investment_transferring/:investment_id',
                method: 'PUT'
            },
            createAssignment: {
                url: '/service/lending/investment_transferring/:investment_id',
                method: 'POST'
            },
            removeAssignment: {
                url: '/service/lending/investment_transferring/:investment_id',
                method: 'DELETE'
            },
            //project interface
            lendApply: {
                url: '/service/lending/application',
                method: 'POST'
            },
            getRepayMethods: {
                url: '/service/lending/repaymentmethod',
                method: 'GET'
            },
            getProjectList: {
                url: '/service/lending/public_project',
                method: 'GET'
            },
            getProject: {
                url: '/service/lending/public_project/:project_id',
                method: 'GET'
            },
            investProject: {
                url: '/service/lending/investment/:project_id',
                method: 'POST'
            },
            getGuarantees: {
                url: '/service/credit/guarantee',
                method: 'GET'
            },
            getGuarantee: {
                url: '/service/credit/guarantee/:id',
                method: 'GET'
            },
            lendStudentApply: {
                url: '/service/lending/finapplication',
                method: 'POST'
            },
            getStudentProjectList: {
                url: '/service/lending/finproject',
                method: 'GET'
            },
            getStudentProject: {
                url: '/service/lending/finproject/:project_id',
                method: 'GET'
            },
            //request phone code
            changePhoneCode: {
                url: '/service/auth/phone_code/current_phone',
                method: 'GET'
            },
            setPhoneCode: {
                url: '/service/auth/phone_code/change_phone',
                method: 'GET'
            },
            setEmailCode: {
                url: '/service/auth/phone_code/email_change',
                method: 'GET'
            },
            setTradeCode: {
                url: '/service/auth/phone_code/trade_password',
                method: 'GET'
            },
            registerCode: {
                url: '/service/auth/register_phone_code/:ver_code',
                method: 'GET'
            },
            retrievePasswordCode: {
                url: '/service/auth/retrieve_password_phone_code/:ver_code',
                method: 'GET'
            },
            withdrawCode: {
                url: '/service/auth/phone_code/withdraw',
                method: 'GET'
            },
            resetPassCode: {
                url: '/service/auth/phone_code/password',
                method: 'GET'
            },
            getStudentApplyBanner: {
                url: '/service/board/banners/student',
                method: 'GET'
            },
            postSourceUser: {
                url: '/service/auth/sourcewebsite',
                method: 'POST'
            },
            getSourceUser: {
                url: '/service/auth/sourcewebsite',
                method: 'GET'
            },
            getMallProduct: {
                url: '/service/mall/commodity',
                method: 'GET'
            },
            getProductDetail: {
                url: '/service/mall/commodity/:commodity_id',
                method: 'GET'
            },
            payProductOrdery: {
                url: '/service/mall/commodity_order/:order_id',
                method: 'POST'
            },
            getProductOrder: {
                url: '/service/mall/commodity_order',
                method: 'GET'
            }
        },
        /*Name: status config
         *Author: Peach
         *Time: 2014-5-18
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
                '300': '提前还款',
            },
            'log': {
                '100': '处理中',
                '200': '处理开始',
                '300': '处理成功',
                '399': '处理失败'
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
            'vip-status': {
                '0': '普通',
                '1': 'VIP',
                '2': 'SVIP',
                '3': '特级'
            }
        },
        /*Name: bankcard style configs
         *Author: Peach
         *Time: 2014-6-3
        */
        bankIconConfig: {
            '中国银行': 'bank-boc',
            '中国农业银行': 'bank-abc',
            '中国建设银行': 'bank-ccb',
            '招商银行': 'bank-cmb',
            '中国工商银行': 'bank-icbc'
        },
        /*Name: all post config
         *Author: Peach
         *Time: 2014-6-17
        */
        postConfig: {
            pagination: 10,  //the number of list in every page
            navs: {
                'about': {
                    name: '关于我们',
                    childs: [
                        {
                            name: '公司简介',
                            type: 0,
                            url: 'info',
                            list: false
                        },
                        {
                            name: '管理团队',
                            type: 1,
                            url: 'manage',
                            list: false
                        },
                        {
                            name: '联系我们',
                            type: 2,
                            url: 'contact',
                            list: false
                        },
                        {
                            name: '合作伙伴',
                            type: 3,
                            url: 'partner',
                            list: false
                        },
                        {
                            name: '办公环境',
                            type: 4,
                            url: 'work-space',
                            list: false
                        },
                        {
                            name: '员工风采',
                             type: 8,
                             url: 'staff-presence',
                             list: false
                        },
                        {
                            name: '公司证件',
                            type: 5,
                            url: 'credential',
                            list: false
                        },
                        {
                            name: '人才招聘',
                            type: 6,
                            url: 'hire',
                            list: false
                        },
                        {
                            name: '专家团队',
                            type: 7,
                            url: 'experts',
                            list: false
                        }
                    ]
                },
                'security': {
                    name: '安全保障',
                    childs: [
                        {
                            name: '安全保障',
                            type: 10,
                            url: 'introduction',
                            list: false
                        },
                        {
                            name: '逾期垫付流程',
                            type: 11,
                            url: 'flow',
                            list: false
                        },
                        {
                            name: '担保机构',
                            type: 13,
                            url: 'guarantee_info',
                            list: false
                        },
                        {
                            name: '政策法规',
                            type: 14,
                            url: 'policies_regulations',
                            list: false
                        }
                    ]
                },
                'law': {
                    name: '法律法规',
                    childs: [
                        {
                            name: '法律法规',
                            type: 20,
                            url: 'introduction',
                            list: false
                        },
                        {
                            name: '政策导向',
                            type: 21,
                            url: 'lead',
                            list: false
                        },
                        {
                            name: '服务条款',
                            type: 22,
                            url: 'provision',
                            list: false
                        }
                    ]
                },
                'help': {
                    name: '帮助中心',
                    childs: [
                        {
                            name: '关于中宝财富',
                            type: 30,
                            url: 'zhongbao',
                            list: false
                        },
                        {
                            name: '关于注册登录',
                            type: 31,
                            url: 'entrance',
                            list: false
                        },
                        {
                            name: '关于充值提现',
                            type: 32,
                            url: 'finance',
                            list: false
                        },
                        {
                            name: '关于利息费用',
                            type: 33,
                            url: 'fee',
                            list: false
                        },
                        {
                            name: '关于安全认证',
                            type: 34,
                            url: 'certify',
                            list: false
                        },
                        {
                            name: '关于债权转让',
                            type: 35,
                            url: 'assignment',
                            list: false
                        },
                        {
                            name: '关于宝币商城',
                            type: 36,
                            url: 'mall',
                            list: false
                        },
						{
                            name: '关于网站规则',
                            type: 42,
                            url: 'rule',
                            list: false
                        },
                    ]
                },
                'newcomer': {
                    name: '新手上路',
                    childs: [
                        {
                            name: '新手上路',
                            type: 40,
                            url: 'track',
                            list: false
                        },
                        {
                            name: '平台原理',
                            type: 41,
                            url: 'principle',
                            list: false
                        },
                       
                        {
                            name: '模式介绍',
                            type: 43,
                            url: 'model',
                            list: false
                        }
                    ]
                },
                'trend': {
                    name: '网站动态',
                    childs: [
                        {
                            name: '网站公告',
                            type: 50,
                            url: 'notice',
                            list: true
                        },
                        {
                            name: '媒体报道',
                            type: 51,
                            url: 'report',
                            list: true,
                            icon: 'icon-globe'
                        },
                        {
                            name: '发标预告',
                            type: 53,
                            url: 'advance',
                            list: true
                        }
                    ]
                }
            }
        }
    });
});
