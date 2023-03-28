# Testing

## Integration Testing

Our primary way of testing is through integration tests, we run a database and
our tests with actual interactions against this database. This allows us to
have a real world understanding of how our code works end to end.

In order to facilitate this there are various helpers available in our
[testhelpers](./internal/testhelpers) package. 

One down side to using an external database to run our tests with is that our
current test suite can not run parallel. This is a sacrifice that we are
aware of and the trade offs are understood. Therefore if you want to run the
tests you will need to run them as follows:

```bash
go test ./... -p 1
```

## We dont like Mocks

There are a couple of reasons we don't like mocks:

- Mocking is testing with only the knowledge of the person writing the mocks,
this could have unforseen side effects in that the person writing the mocks
might misunderstand how something works and create their code to work against
their understandings and not against how it actually works.

- Mocks are shallow, so in order to really make use of them you need to write/generate a lot of code. 

- Mocks ensure your code works against a mock, there is no assurance from this
  that your code will work against the real world scenario 

## When to use mocks

Generally it might be difficult to fake a error in an integration tests, so we
have used some mocks when creating our database functions in the [storage
directroy](./internal/storage). This is the only place we will be using mocks.

**Other than in the above scenario please do not use Mocks**




