const mocha = require('mocha')
const chai = require('chai').should()
const mocks = require('./mocks/typeform-form')

const translateFunctions = require('../app/translate-fields')

describe('should translate the welcome screen', () => {
  const data = mocks.welcome_screens[0]
  const translated = translateFunctions.translateWelcomeScreen(data)
  
  it('should have a text property with the title of the welcome screen', () => {
    translated.should.have.property('text', data.title)
  })
  it('should have a quick_replies property of type array', () => {
    translated.quick_replies.should.be.an('array')
  })
  it('quick_replies should have one element in it', () => {
    translated.quick_replies.should.have.length(1)
  })
  it('quick_replies should contain objects with properties of content_type, title and payload', () => {
    translated.quick_replies.forEach(reply => {
      reply.should.have.property('content_type', 'text')
      reply.should.have.property('title')
      reply.should.have.property('payload', data.properties.button_text)
    })
  })
})

describe('should translate short text questions', () => {
  const shortTextQuestion = mocks.fields.filter(question => {
    return question.type === 'short_text'
  })[0]

  const question = translateFunctions.translateShortText(shortTextQuestion)
  
  it('should have a text property that is the Typeform question', () => {
    question.should.have.property('text', shortTextQuestion.title)
  })
})

describe('should translate statement', () => {
  const statement = mocks.fields.filter(question => {
    return question.type === 'statement'
  })[0]

  const translated = translateFunctions.translateStatement(statement)

  it('should have a text property with the title of the statement', () => {
    translated.should.have.property('text', statement.title)
  })

  it('quick_replies should have one element in it', () => {
    translated.quick_replies.should.have.length(1)
  })

  it('quick_replies should contain objects with properties of content_type, title and payload', () => {
    translated.quick_replies.forEach(reply => {
      reply.should.have.property('content_type', 'text')
      reply.should.have.property('title')
      reply.should.have.property('payload', statement.properties.button_text)
    })
  })
})

describe('should translate long_text questions', () => {
  const longTextQuestion = mocks.fields.filter(question => {
    return question.type === 'long_text'
  })[0]

  const question = translateFunctions.translateLongText(longTextQuestion)

  it('should have a text property that is the Typeform question', () => {
    question.should.have.property('text', longTextQuestion.title)
  })
})

describe('should translate yes/no questions', () => {
  const yesNoQuestion = mocks.fields.filter(question => {
    return question.type === 'yes_no'
  })[0]

  const translated = translateFunctions.translateYesNo(yesNoQuestion)

  it ('should have a text property with the title of the questions', () => {
    translated.should.have.property('text', yesNoQuestion.title)
  })
  it ('should have a quick_replies property of type array', () => {
    translated.quick_replies.should.be.an('array')
  })
  it ('quick_replies should have exactly two elements in it', () => {
    translated.quick_replies.should.have.length(2)
  })
  it('quick_replies should contain objects with properties of content_type, title and payload', () => {
    translated.quick_replies.forEach(reply => {
      reply.should.have.property('content_type', 'text')
      reply.should.have.property('title')
      reply.should.have.property('payload')
    })
  })
  it ('The first option given by quick_replies should be a "yes"', () => {
    translated.quick_replies[0].title.should.equal('yes')
  })
  it('The first payload should return a "yes"', () => {
    translated.quick_replies[0].payload.should.equal('yes')
  })  
  it('The second option given by quick_replies should be a "no"', () => {
    translated.quick_replies[1].title.should.equal('no')
  })
  it('The second payload should return a "no"', () => {
    translated.quick_replies[1].payload.should.equal('no')
  })
})

describe('should translate multiple choice questions', () => {

  const multipleChoiceQuestion = mocks.fields.filter(question => {
    return question.type === 'multiple_choice'
  })[0]

  const question = translateFunctions.translateMultipleChoice(multipleChoiceQuestion)

  it('should not have a text property', () => {
    question.should.not.have.property('text')
  })
  it('should have an attachment property', () => {
    question.should.have.property('attachment')
  })
  it('should have an attachment property of "type" : template', () => {
    question.attachment.should.have.property('type', 'template')
  })
  it('should have an attachment property "payload"', () => {
    question.attachment.should.have.property('payload')
  })
  it('should have a payload with property of "template_type" : button', () => {
    question.attachment.payload.should.have.property('template_type', 'button')
  })
  it('should have a payload with property of "text" as the question title', () => {
    question.attachment.payload.should.have.property('text', multipleChoiceQuestion.title)
  })
  it('should have a payload with property of buttons that is an array', () => {
    question.attachment.payload.buttons.should.be.an('array')
  })
  it('should have buttons with type, title and payload ', () => {
    const fbButtons = question.attachment.payload.buttons
    const tfChoices = multipleChoiceQuestion.properties.choices
    for ([index, el] of fbButtons.entries()) {
      el.should.have.property('type', 'postback')
      el.should.have.property('title', tfChoices[index].label)
      el.should.have.property('payload')
    }
  })
})

describe('should translate questions asking for email', () => {
  const emailQuestion = mocks.fields.filter(question => {
    return question.type === 'email'
  })[0]

  const translated = translateFunctions.translateEmail(emailQuestion)

  it('should have a text property with the title of the questions', () => {
    translated.should.have.property('text', emailQuestion.title)
  })
  it('should have a quick_replies property of type array', () => {
    translated.quick_replies.should.be.an('array')
  })
  it('quick_replies should have one element in it', () => {
    translated.quick_replies.should.have.length(1)
  })
  it('quick_reply should be an object with property "content_type" of "user_email"', () => {
    translated.quick_replies[0].should.have.property('content_type', 'user_email')
  })
  it('quick_reply should be an object with property "title"', () => {
    translated.quick_replies[0].should.have.property('title', 'send email')
  })
  it('quick_reply should not have property "payload"', () => {
    translated.quick_replies[0].should.not.have.property('payload')
  })
})

describe('should translate questions that use an opinion scale', () => {
  const opinionScaleQuestions = mocks.fields.filter(question => {
    return question.type === 'opinion_scale'
  })[0]

  const translated = translateFunctions.translateOpinionScale(opinionScaleQuestions)

  it('should have a text property with the title of the questions', () => {
    translated.should.have.property('text', opinionScaleQuestions.title)
  })
  it('should have a quick_replies property of type array', () => {
    translated.quick_replies.should.be.an('array')
  })
  it('quick_replies should have 5 elements in it', () => {
    translated.quick_replies.should.have.length(5)
  })
  it('quick_replies should have "content-type", "title", "payload" properties', () => {
    translated.quick_replies.every(reply => {
      if (reply.content_type && reply.title && reply.payload) {
        return true
      }
    }).should.equal(true)
  })
  it('quick_replies payload property should return the score', () => {
    for ([index, el] of translated.quick_replies.entries()) {
      el.payload.choice.should.equal(++index)
      el.payload.base.should.equal(5)
    }
  })
})

describe('should translate questions that ask for a rating', () => {
  const ratingQuestion = mocks.fields.filter(question => {
    return question.type === 'rating'
  })[0]

  const translated = translateFunctions.translateRatings(ratingQuestion)

  it('should have a text property with the title of the questions', () => {
    translated.should.have.property('text', ratingQuestion.title)
  })
  it('should have a quick_replies property of type array', () => {
    translated.quick_replies.should.be.an('array')
  })
  it('quick_replies should have n elements as specified in question', () => {
    translated.quick_replies.should.have.length(ratingQuestion.properties.steps)
  })
  it('quick_replies should have "content-type", "title", "payload" properties', () => {
    translated.quick_replies.every(reply => {
      if (reply.content_type && reply.title && reply.payload) {
        return true
      }
    }).should.equal(true)
  })
  it('quick_replies title and payload should increment by one', () => {
    let counter = translated.quick_replies[0].title
    for (let [index, reply] of translated.quick_replies.entries()) {
      const payloadArr = reply.payload.split(' ')
      reply.title.should.equal(counter)
      Number(payloadArr[0]).should.equal(counter)
      Number(payloadArr[payloadArr.length-1]).should.equal(ratingQuestion.properties.steps)
      counter ++
    }
  })
})

describe('should translate questions with choices accompanied by pictures', () => {
  const pictureChoiceQuestion = mocks.fields.filter(question => {
    return question.type === 'picture_choice'
  })[0]

  const translated = translateFunctions.translatePictureChoice(pictureChoiceQuestion)
  
  it('should have an attachment property', () => {
    translated.should.have.property('attachment')
  })

  const attachment = translated.attachment

  it('attachment should have property type set to template', () => {
    attachment.should.have.property('type', 'template')
  })
  it('attachment should have payload property', () => {
    attachment.should.have.property('payload')
  })
  it('payload should have template type set to generic', () => {
    attachment.payload.should.have.property('template_type', 'generic')
  })
  it('payload should have an elements array equal to length of choices', () => {
    attachment.payload.elements.should.have.length(pictureChoiceQuestion.properties.choices.length)
  })

  const fbElements = attachment.payload.elements
  const tfChoices = pictureChoiceQuestion.properties.choices

  it('each element should have a title property', () => {
    fbElements.forEach(el => el.should.have.property('title', pictureChoiceQuestion.title))
  })

  it('each element should have a button array with one element', () => {
    fbElements.forEach(el => el.buttons.should.have.length(1))
  })

  it('each element should have a image_url property', () => {
    for ([index, el] of fbElements.entries()) {
      el.image_url.should.equal(tfChoices[index].attachment.href)
    }
  })

  it('each button should be type of postback', () => {
    fbElements.forEach(el => {
      el.buttons.forEach(button => button.should.have.property('type', 'postback'))
    })
  })

  it('each button should have a title equal to the choice label', () => {
    for ([index, el] of fbElements.entries()) {
      el.buttons[0].should.have.property('title', `select ${tfChoices[index].label}`) 
    }
  })

  it('each button should have a payload', () => {
    for ([index, el] of fbElements.entries()) {
      el.buttons[0].should.have.property('payload', tfChoices[index].label)
    }
  })
})
