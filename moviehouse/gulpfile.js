const gulp = require('gulp');
const mustache = require('gulp-mustache');
require('dotenv').config();

gulp.task('replace', function() {
  return gulp.src(['./src/script.js', './src/index.html', './src/style.css'])
    .pipe(mustache(process.env))
    .pipe(gulp.dest('./dist'))
});