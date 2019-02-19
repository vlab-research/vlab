$(() => {
  const iframe = $('iframe');
  const player = new Vimeo.Player(iframe);
  
  player.getVideoTitle().then(title => {
    console.log('title:', title);
  });
  
  player.on('play', event => {
    console.log('Played the video', event);
  });

  player.on('pause', event => {
    console.log('Paused the video', event);
  });

  player.on('ended', event => {
    console.log('Video ended', event);
  });
});