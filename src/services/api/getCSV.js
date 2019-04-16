import ApiClient from '.';

export default function getCsv(formid) {
  ApiClient.fetcher({ path: `/responses/${formid}/csv` })
    .then(async res => ({
      filename: res.headers
        .get('Content-Disposition')
        .split('filename="')[1]
        .slice(0, -1),
      blob: await res.blob(),
    }))
    .then(obj => {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(obj.blob);
      a.download = obj.filename;
      a.click();
    });
}
