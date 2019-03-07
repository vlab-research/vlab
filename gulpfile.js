const gulp = require('gulp');
const replace = require('gulp-replace');

gulp.task('replace', function() {
  const serverUrl = 'http://localhost:3001/events';
  return gulp.src(['./src/script.js', './src/index.html', './src/style.css'])
    .pipe(replace('{{SERVER_URL}}', serverUrl))
    .pipe(gulp.dest('./dist'))
});