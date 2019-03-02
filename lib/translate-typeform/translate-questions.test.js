const mocha = require('mocha')
const chai = require('chai').should()
const mocks = require('./mocks/typeform-form')

const translateFunctions = require('./translate-fields')

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

describe('translateShare', () => {
  it('associates url, text, and buttonText', () => {
    // TODO: test!
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

  it('should have metadata with type statement', () => {
    translated.metadata.should.have.property('type', 'statement')
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

describe('yes_no questions', () => {
  const yesNoQuestion = mocks.fields.filter(question => {
    return question.type === 'yes_no'
  })[0]

  const translated = translateFunctions.translator(yesNoQuestion)

  it('should have a text property with the title of the questions', () => {
    translated.attachment.payload.should.have.property('text', yesNoQuestion.title)
  })

  it('The options given by buttons should be a "yes" and "no"', () => {
    translated.attachment.payload.buttons[0].title.should.equal('Yes')
    translated.attachment.payload.buttons[1].title.should.equal('No')
  })

  it('The payload given by buttons should be a true/false and contain ref', () => {
    JSON.parse(translated.attachment.payload.buttons[0].payload).value.should.equal(true)
    JSON.parse(translated.attachment.payload.buttons[1].payload).value.should.equal(false)
    JSON.parse(translated.attachment.payload.buttons[0].payload).ref.should.equal(yesNoQuestion.ref)
  })
})

describe('should translate multiple choice questions', () => {

  const multipleChoiceQuestion = mocks.fields.filter(question => {
    return question.type === 'multiple_choice'
  })[0]

  const translated = translateFunctions.translator(multipleChoiceQuestion)

  it('should have a text property with the title of the questions', () => {
    translated.should.have.property('text', multipleChoiceQuestion.title)
  })
  it('quick_replies should be an array with 3 elements in it', () => {
    translated.quick_replies.should.be.an('array')
    translated.quick_replies.should.have.length(3)
  })
  it('quick_replies should have "content-type", "title", "payload" properties', () => {
    translated.quick_replies.every(reply => {
      if (reply.content_type && reply.title && reply.payload) {
        return true
      }
    }).should.equal(true)
  })
  it('quick_replies should have the proper payload and titles', () => {
    const values = translated.quick_replies.map(r => JSON.parse(r.payload)).map(r => r.value)
    values.should.deep.equal(['Commander', 'Astro-biologist', 'Engineer'])
    const titles = translated.quick_replies.map(r => r.title)
    titles.should.deep.equal(['Commander', 'Astro-biologist', 'Engineer'])
  })
})

describe('should translate questions that use an opinion scale', () => {
  const opinionScaleQuestion = mocks.fields.filter(question => {
    return question.type === 'opinion_scale'
  })[0]

  const translated = translateFunctions.translateOpinionScale(opinionScaleQuestion, 'foo')

  it('should have a text property with the title of the questions', () => {
    translated.should.have.property('text', opinionScaleQuestion.title)
  })

  it('quick_replies should have number of elements equal to steps', () => {
    translated.quick_replies.should.be.an('array')
    translated.quick_replies.should.have.length(opinionScaleQuestion.properties.steps)
  })


  it('quick_replies payload property should return the score and ref', () => {
    for ([index, el] of translated.quick_replies.entries()) {
      JSON.parse(el.payload).value.should.equal('' + (index+1))
      JSON.parse(el.payload).ref.should.equal('foo')
      el.title.should.equal('' + (index+1))
      el.content_type.should.equal('text')
    }
  })

  it('quick_replies payload property should listen to start_at_one', () => {
    const translated = translateFunctions.translateOpinionScale({...opinionScaleQuestion,
                                                                 properties: { steps: 5, start_at_one: false }})

    for ([index, el] of translated.quick_replies.entries()) {
      JSON.parse(el.payload).value.should.equal('' + (index))
      el.title.should.equal('' + (index))
      el.content_type.should.equal('text')
    }
  })

  it('quick_replies payload property should default to 1 if start_at_one is undefined (translateRating)', () => {
    const translated = translateFunctions.translateRatings({...opinionScaleQuestion,
                                                            properties: { steps: 5, start_at_one: undefined }})

    for ([index, el] of translated.quick_replies.entries()) {
      JSON.parse(el.payload).value.should.equal('' + (index+1))
      el.title.should.equal('' + (index+1))
      el.content_type.should.equal('text')
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
