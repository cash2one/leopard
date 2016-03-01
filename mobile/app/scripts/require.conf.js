requirejs.config({
  baseUrl: '/',
  waitSeconds: 15,
  urlArgs: 'bust=' + new Date().getTime(),
  paths: {
    // Libraries
    'jQuery': 'bower_components/jquery/dist/jquery.min',
    'ionic': 'scripts/lib/ionic.bundle',
    'ngLocalstorage': 'bower_components/angular-local-storage/dist/angular-local-storage.min',
    // module, config, router, directive, service, controllers
    'app': 'scripts/app',
    'truffleConfig': 'scripts/config',
    'truffleRoute': 'scripts/route',
    'truffleDirective': 'scripts/directive',
    'truffleService': 'scripts/service',
    'truffleController': 'scripts/controller'
  },
  shim: {
    'jQuery': {
      exports: 'jQuery'
    },
    'ionic': {
      deps: ['jQuery']
    },
    'ngLocalstorage': {
      deps: ['ionic']
    }
  }
});
require(['ionic', 'app'], function() {

  'use strict';

  angular.bootstrap(document, ['truffleMobile']);

});
