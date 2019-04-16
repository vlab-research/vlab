'use strict';

const SERVER_URL = '{{{SERVER_URL}}}';
const params = new URLSearchParams(window.location.search);
const videoId = params.get('id');
let psid;

function handleEvent(data, eventType) {
  const xhr = new XMLHttpRequest();
  xhr.open('POST', SERVER_URL);
  xhr.setRequestHeader('Content-Type', 'application/json');
  xhr.send(JSON.stringify({ data, eventType, psid }));
}

function handleError(err, title, message) {
  const div = document.createElement('div');
  div.classList.add("error-container");
  div.innerHTML = `<h1>${title}</h1><p>${message}</p>`;
  document.querySelector('.container').innerHTML = ``
  document.querySelector('.container').appendChild(div);
  console.error(err);
}

function setPlayer() {
  const options = {
    id: videoId,
    responsive: true
  };

  const player = new Vimeo.Player('vimeoVideo', options);

  player.ready().then(() => {
    player.on('ended', data => handleEvent(data, 'ended'));

    player.on('error', data => handleEvent(data, 'error'));

    player.on('pause', data => handleEvent(data, 'pause'));

    player.on('play', data => handleEvent(data, 'play'));

    player.on('playbackratechange', data => handleEvent(data, 'playbackratechange'));

    player.on('seeked', data => handleEvent(data, 'seeked'));

    player.on('volumechange', data => handleEvent(data, 'volumechange'));
  }).catch((err) => {
    const title = '❌ Not found';
    const message = 'Sorry, we couldn’t find that video'
    handleError(err, title, message);    
  });
}

document.addEventListener('DOMContentLoaded', () => {
  window.extAsyncInit = function () {
    MessengerExtensions.getContext('{{{APP_ID}}}',
      function success(thread_context) {
        psid = thread_context.psid;
        setPlayer();
      },
      function error(err) {
        const title = '🔒Forbidden';
        const message = 'It seems you are not logged in with facebook'
        handleError(err, title, message);
      }
    );
  };
});