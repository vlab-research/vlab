function shareButton(title, url) {
  return {
    "type": "element_share",
    "share_contents": {
      "attachment": {
        "type": "template",
        "payload": {
          "template_type": "generic",
          "elements": [
            {
              "title": title,
              // "subtitle": "<TEMPLATE_SUBTITLE>",
              // "image_url": "<IMAGE_URL_TO_DISPLAY>",
              "default_action": {
                "type": "web_url",
                "url": url
              },
              "buttons": [
                {
                  "type": "web_url",
                  "url": url,
                  "title": title
                }
              ]
            }
          ]
        }
      }
    }
  }
}

function shareMessage(title, url) {
  return {
    "attachment":{
      "type":"template",
      "payload":{
        "template_type":"button",
        "text": "Do you wish to share this?",
        "buttons": [ shareButton(title, url)]
      }
    },
    metadata: '{ "ref": "foobarbaz"}' // Get the ref from the question
  }
}

module.exports = { shareMessage }
