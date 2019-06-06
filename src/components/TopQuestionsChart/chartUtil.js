const mockResultSet = {
  rawData: () => [
    { 'Responses.questionId': 'How are you?', 'Responses.count': 10 },
    { 'Responses.questionId': 'Where do you come from?', 'Responses.count': 1 },
    { 'Responses.questionId': 'Are you ready?', 'Responses.count': 5 },
    { 'Responses.questionId': 'Are you ready?', 'Responses.count': 4 },
    { 'Responses.questionId': 'Are you ready?', 'Responses.count': 3 },
    { 'Responses.questionId': 'Are you ready?', 'Responses.count': 2 },
    { 'Responses.questionId': 'Are you ready?', 'Responses.count': 2 },
    { 'Responses.questionId': 'Are you ready?', 'Responses.count': 2 },
    { 'Responses.questionId': 'Are you ready?', 'Responses.count': 2 },
    { 'Responses.questionId': 'Are you ready?', 'Responses.count': 2 },
  ],
};

export const computeChartData = (resultSet, interval) => {
  return mockResultSet
    .rawData()
    .map(question => ({
      question: question['Responses.questionId'],
      answers: question['Responses.count'],
    }))
    .sort((a, b) => b.answers - a.answers)
    .slice(0, interval);
};
