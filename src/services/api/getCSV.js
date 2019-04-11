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
      const url = URL.createObjectURL(obj.blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = obj.filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
    });
}
