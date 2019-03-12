const gulp = require('gulp');
const mustache = require('gulp-mustache');
require('dotenv').config();

gulp.task('replace', function() {
  return gulp.src(['./src/script.js', './src/index.html', './src/style.css'])
    .pipe(mustache({ SERVER_URL: process.env.SERVER_URL }))
    .pipe(gulp.dest('./dist'))
});