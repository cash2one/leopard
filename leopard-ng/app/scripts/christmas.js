define(['angular', 'snow'], function(){
    'use strict';

    return angular.module('christmas', [])
        .run(['$cookies', '$location', '$timeout', '$document', function($cookies, $location, $timeout, $document){
            var topContainer = $document.find('.nav-top'),
                body = $document.find('body');

            //modify text color for all element, just for [zhongbao]
            topContainer.find('#aid *, .index-service, .index-phone').css('color', '#e3e3e3');
            topContainer.find('#aid a').mouseover(function(){
                $(this).css('color', '#fff');
            });
            topContainer.find('#aid a').mouseout(function(){
                $(this).css('color', '#e3e3e3');
            });
            topContainer.find('.index-service img').attr('src', '/images/christmas/mobile.png');
            //modify text color for all element, just for zhongbao

            //modify top background color
            topContainer.css('backgroundColor', '#b30200');

            //add star to top
            topContainer.css({
                backgroundImage: 'url("/images/christmas/stars.png")',
                backgroundRepeat: 'repeat-x',
                backgroundPosition: '0 -15px'
            });

            // add snow to top
            function addSnow(){
                var snow = jQuery('<div></div');
                snow.css({
                    position: 'absolute',
                    zIndex: 1,
                    top: topContainer.offset().top + topContainer.outerHeight() - 6,
                    display: 'none',
                    width: '100%',
                    height: 55,
                    backgroundImage: 'url("/images/christmas/snow.png")',
                    backgroundRepeat: 'none',
                    backgroundPosition: 'center top'
                });

                body.append(snow);

                snow.fadeIn(300);
            }

            //add decoration
            function addDecoration(){
                var decoration = jQuery('<div></div>');
                decoration.css({
                    position: 'absolute',
                    zIndex: 2,
                    top: -97,
                    left: '50%',
                    marginLeft: -104,
                    width: 208,
                    height: 97,
                    backgroundImage: 'url(/images/christmas/decoration.png)'
                });

                var rightDeco = jQuery('<div></div>');
                rightDeco.css({
                    position: 'absolute',
                    zIndex: 2,
                    top: -30,
                    left: -30,
                    width: 150,
                    height: 143,
                    backgroundImage: 'url(/images/christmas/left_deco.png)'
                });

                var leftDeco = jQuery('<div></div>');
                leftDeco.css({
                    position: 'absolute',
                    zIndex: 2,
                    top: -20,
                    right: 0,
                    width: 80,
                    height: 163,
                    backgroundImage: 'url(/images/christmas/right_deco.png)'
                });

                body.append(decoration).append(rightDeco).append(leftDeco);

                decoration.animate({top: -10}, 300);
            }

            //excute change after document loaded
            $document.ready(function(){
                $timeout(function(){
                    addSnow();
                    addDecoration();
                    if(!$cookies['is_show_christmas'] &&
                        (new Date().getDate() == 25 || new Date().getDate() == 24)){
                        showBelessing();
                        $cookies['is_show_christmas'] = true;
                    }
                }, 800);
            })

            if($location.path() == '/'){
                //render snow
                createSnow('/', 100);

                //rmeove snow
                $timeout(function(){
                    removeSnow();
                }, 28000);
            }

            //show blessing and marry christmas
            function showBelessing(){
                //init backdrop
                var backdrop = jQuery('<div></div>');
                backdrop.css({
                    position: 'absolute',
                    zIndex: 100,
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: $document.height(),
                    backgroundColor: '#000',
                    opacity: 0.3
                });

                backdrop.click(function(){
                    removeAll();
                });

                //init images
                var blessing = jQuery('<div></div>'),
                    giftsBg = jQuery('<div></div>'),
                    marryChristmas = jQuery('<div><img width="0" src="/images/christmas/marry_christmas.png"></div>'),
                    gifts = [
                        jQuery('<img src="/images/christmas/gift_0.png">'),
                        jQuery('<img src="/images/christmas/gift_1.png">'),
                        jQuery('<img src="/images/christmas/gift_2.png">'),
                        jQuery('<img src="/images/christmas/gift_3.png">'),
                        jQuery('<img src="/images/christmas/gift_4.png">'),
                        jQuery('<img src="/images/christmas/gift_5.png">')
                    ],
                    imgQueue = ['blessing.png', 'marry_christmas.png', 'gifts_bg.png'
                        , 'gift_0.png', 'gift_1.png', 'gift_2.png', 'gift_3.png'
                        , 'gift_4.png', 'gift_5.png'],
                    loadedCount = 0,
                    giftPos = [
                        {
                            marginLeft: 270,
                            marginTop: -160,
                            opacity: 1
                        },
                        {
                            marginLeft: -300,
                            marginTop: 30,
                            opacity: 1
                        },
                        {
                            marginLeft: -340,
                            marginTop: -52,
                            opacity: 1
                        },
                        {
                            marginLeft: -280,
                            marginTop: -180,
                            opacity: 1
                        },
                        {
                            marginLeft: -40,
                            marginTop: -190,
                            opacity: 1
                        },
                        {
                            marginLeft: 260,
                            marginTop: -5,
                            opacity: 1
                        }
                    ];

                blessing.css({
                    position: 'fixed',
                    zIndex: 1001,
                    top: 50,
                    left: '50%',
                    display: 'none',
                    marginLeft: -171,
                    width: 343,
                    height: 58,
                    backgroundImage: 'url(/images/christmas/blessing.png)'
                });

                marryChristmas.css({
                    position: 'fixed',
                    zIndex: 1003,
                    top: 140,
                    left: '50%',
                    marginLeft: -225,
                    width: 450,
                    height: 249,
                    textAlign: 'center',
                    lineHeight: '249px'
                });

                giftsBg.css({
                    position: 'fixed',
                    zIndex: 1001,
                    top: 140,
                    left: '50%',
                    marginLeft: -303,
                    width: 606,
                    height: 402,
                    backgroundImage: 'url(/images/christmas/gifts_bg.png)'
                })

                initGifts();

                for(var i = 0;i<imgQueue.length;i++){
                    var img = new Image();
                    img.onload = loadedImage;

                    img.src = '/images/christmas/' + imgQueue[i];
                }

                function loadedImage(){
                    loadedCount++;

                    if(loadedCount == imgQueue.length){
                        body.append(backdrop).append(blessing)
                            .append(giftsBg).append(marryChristmas).append(gifts);

                        blessing.fadeIn(function(){
                            animateGifts();
                            $timeout(function(){
                                marryChristmas.find('img').animate({width: '120%'}, 300, function(){
                                    $(this).animate({width: '100%'}, 200);
                                });
                            }, 400);
                        });

                        $timeout(function(){
                            removeAll();
                        }, 8000)
                    }
                }

                function initGifts(){
                    for(var i = 0;i<gifts.length;i++){
                        gifts[i].css({
                            position: 'fixed',
                            zIndex: 1002,
                            top: 300,
                            left: '50%',
                            opacity: 0,
                            width: 80
                        });
                    }
                }

                function animateGifts(){
                    for(var i = 0;i<gifts.length;i++){
                        (function(index){
                            $timeout(function(){
                                gifts[index].animate(giftPos[index], 500);
                            }, 40*index);
                        })(i)
                    }
                }

                function removeAll(){
                    blessing.remove();
                    giftsBg.remove();
                    marryChristmas.remove();
                    for(var i = 0;i<gifts.length;i++)
                        gifts[i].remove();
                    backdrop.remove();
                }
            }
        }]);
})
