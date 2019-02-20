'use strict';

function handleEvent (data, type) {
  console.log(type, data);
}

$(() => {
  const options = {
    id: 280815263,
    width: 800
  };
  const player = new Vimeo.Player('vimeoVideo', options);
  
  player.on('error', data => handleEvent(data, 'error'));

  player.on('loaded', data => handleEvent(data, 'loaded'));

  player.on('play', data => handleEvent(data, 'play'));

  player.on('pause', data => handleEvent(data, 'pause'));

  player.on('ended', data => handleEvent(data, 'ended'));
});