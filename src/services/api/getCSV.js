import ApiClient from '.';

export default function getCsv(formids) {
  const ids = formids.join(',');

  ApiClient.fetcher({ path: `/responses/csv?formids=${ids}` })
    .then(async (res) => {
      if (res.status !== 200) {
        throw new Error(`Error fetching CSV Form: ${formids} Error: ${res.statusText}`);
      }
      return {
        filename: res.headers
          .get('Content-Disposition')
          .split('filename="')[1]
          .slice(0, -1),
        blob: await res.blob(),
      };
    })
    .then((obj) => {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(obj.blob);
      a.download = obj.filename;
      a.click();
    })
    .catch((err) => {
      console.error(err); // eslint-disable-line no-console
    });
}
