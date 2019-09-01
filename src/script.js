'use strict';

const SERVER_URL = '{{{SERVER_URL}}}';
const params = new URLSearchParams(window.location.search);
const videoId = params.get('id');

function handleEvent(psid, eventType) {
  return function sendEvent(data) {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', SERVER_URL);
    xhr.setRequestHeader('Content-Type', 'application/json');

    // add ID of video to event...
    xhr.send(JSON.stringify({ user:psid, data, event: { type: 'event', value: { type: `moviehouse:${eventType}`, id: videoId } }}));
  }
}

function handleError(err, title, message) {
  const div = document.createElement('div');
  div.classList.add("error-container");
  div.innerHTML = `<h1>${title}</h1><p>${message}</p>`;
  document.querySelector('.container').innerHTML = ``
  document.querySelector('.container').appendChild(div);
  console.error(err);
}

function setPlayer(psid) {
  const options = {
    id: videoId,
    responsive: true
  };

  const player = new Vimeo.Player('vimeoVideo', options);

  player.ready().then(() => {
    player.on('ended', handleEvent(psid, 'ended'));

    player.on('error', handleEvent(psid, 'error'));

    player.on('pause', handleEvent(psid, 'pause'));

    player.on('play', handleEvent(psid, 'play'));

    player.on('playbackratechange', handleEvent(psid, 'playbackratechange'));

    player.on('seeked', handleEvent(psid, 'seeked'));

    player.on('volumechange', handleEvent(psid, 'volumechange'));

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
        setPlayer(thread_context.psid);
      },
      function error(err) {
        const title = '🔒Forbidden';
        const message = 'It seems you are not logged in with facebook'
        handleError(err, title, message);
      }
    );
  };
});
