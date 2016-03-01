var gulp = require('gulp');
var gutil = require('gulp-util');
var bower = require('bower');
var less = require('gulp-less');
var minifyCss = require('gulp-minify-css');
var rename = require('gulp-rename');
var connect = require('gulp-connect');
var rjs = require('gulp-requirejs');
var cheerio = require('cheerio')
var fs = require('fs');
var Q = require('q');
var hash = require('gulp-hash-filename');
var uglify = require('gulp-uglify');
var paths = {
  mainLess: './app/styles/less/truffle_mobile.less',
  less: ['./app/styles/less/*.less'],
  html: ['./app/index.html', './app/views/**/*.html'],
  js: ['./app/scripts/**/*.js']
};
var serverPort = 5006;
var livePort = 35726;
var projectFile = 'truffle_mobile';
gulp.task('default', ['dev', 'less', 'runserver', 'watch']);
gulp.task('runserver', function() {
  connect.server({
    root: './app',
    port: serverPort,
    livereload: {
      port: livePort
    }
  });
})

function getFileName(file) {
  return file.substring(file.lastIndexOf('/') + 1);
}

function notifyReload(event) {
  if (!event.path || !event) return;
  gulp.src(event.path).pipe(connect.reload(gutil.log(gutil.colors.magenta(getFileName(getFileName(event.path))) + ' was reloaded.')));
}
gulp.task('less', function() {
  lessTask()
});

function lessTask(event) {
  if (event) gutil.log('Compiling ' + gutil.colors.cyan('less') + '...');
  gulp.src(paths.mainLess)
    .pipe(less())
    .on('error', function(e){
      gutil.beep();
      gutil.log(e);
    })
    .pipe(gulp.dest('./app/styles/'))
    .on('end', function() {
    if (event) {
      gutil.log(gutil.colors.cyan('Less') + ' has been compiled.');
      notifyReload(event);
    }
  });
}
gulp.task('watch', function() {
  gulp.watch(paths.less, lessTask);
  gulp.watch(paths.html, notifyReload);
  gulp.watch(paths.js, notifyReload);
});
gulp.task('install', function() {
  return bower.commands.install().on('log', function(data) {
    gutil.log('bower', gutil.colors.cyan(data.id), data.message);
  });
});
gulp.task('dev', function() {
  var deferred = Q.defer();
  fs.readFile(paths.html[0], function(error, data) {
    if (error) return console.log(error);
    var $ = cheerio.load(data, {
      decodeEntities: false
    });
    $('html').find('link').each(function() {
      if ($(this).attr('href').indexOf(projectFile) != -1) {
        $(this).attr('href', 'styles/' + projectFile + '.css');
      }
    });
    $('html').find('script[data-main]').attr('data-main', 'scripts/require.conf');
    if (!$('body').find('script#_livereload_').length) $('body').append('<script id="_livereload_" src="http://127.0.0.1:' + livePort + '/livereload.js?ext=Chrome&amp;extver=2.0.9"></script>');
    fs.writeFile(paths.html[0], new Buffer($.html(), 'utf-8').toString(), function(error) {
      if (error) return console.log(error);
      gutil.log(gutil.colors.cyan('Reference') + ' has been updated.');
      deferred.resolve();
    });
  });
  return deferred.promise;
})
gulp.task('build', function() {
  var deferred = Q.defer(),
    cssFile = null,
    jsFile = null;
  //compile less
  gutil.log('Compiling ' + gutil.colors.cyan('less') + '...');
  gulp.src(paths.mainLess).pipe(less()).pipe(minifyCss({
    keepSpecialComments: 0
  })).pipe(hash({
    format: '{name}_{hash}{ext}'
  })).pipe(rename(function(path) {
    //cut down the hash code
    var t = path.basename.split('_');
    t[t.length - 1] = t[t.length - 1].substring(0, 10);
    path.basename = t.join('_');
    cssFile = path.basename + path.extname;
    path.basename;
  })).pipe(gulp.dest('./app/styles/')).on('end', function() {
    gutil.log(gutil.colors.cyan('Less') + ' has been compiled.');
  });
  //compress js
  gutil.log('Compressing ' + gutil.colors.cyan('javascript') + '...');
  gulp.src('./app/scripts/require.conf.js').pipe(rjs({
    baseUrl: 'app/',
    name: 'scripts/require.conf',
    mainConfigFile: 'app/scripts/require.conf.js',
    out: 'main.js'
  })).pipe(gulp.dest('./app/scripts/')).on('end', function() {
    gulp.src('./app/scripts/main.js').pipe(uglify()).pipe(hash({
      format: '{name}_{hash}{ext}'
    })).pipe(rename(function(path) {
      //cut down the hash code
      var t = path.basename.split('_');
      t[t.length - 1] = t[t.length - 1].substring(0, 10);
      path.basename = t.join('_');
      jsFile = path.basename;
    })).pipe(gulp.dest('./app/scripts/')).on('end', function() {
      //delete the main.js
      fs.unlink('./app/scripts/main.js');
      gutil.log(gutil.colors.cyan('Javascript') + ' has been compressed.');
      //update index.html
      gutil.log('Updating ' + gutil.colors.cyan('reference') + ' in index.html...');
      fs.readFile(paths.html[0], function(error, data) {
        if (error) return console.log(error);
        var $ = cheerio.load(data, {
          decodeEntities: false
        });
        $('html').find('link').each(function() {
          if ($(this).attr('href').indexOf(projectFile) != -1) {
            $(this).attr('href', 'styles/' + cssFile);
          }
        });
        $('html').find('script[data-main]').attr('data-main', 'scripts/' + jsFile);
        $('body').find('script#_livereload_').remove();
        fs.writeFile(paths.html[0], new Buffer($.html(), 'utf-8').toString(), function(error) {
          if (error) return console.log(error);
          gutil.log(gutil.colors.cyan('Reference') + ' has been updated.');
          deferred.resolve();
        });
      });
    })
  })
  return deferred.promise;
});
