const fs = require('fs/promises');
const fsEvents = require('fs')
const { parse } = require("csv-parse");

const CSV_NUMBERS = [
  'numCitations',
  'pubYear'
]

async function fromCsv(path) {
  let header = null
  const data = {}
  await new Promise(resolve => {
    fsEvents.createReadStream(path).pipe(parse({})).on('data', (d) => {
      if (!header) {
        header = d
      } else {
        id = d[0].toString()
        data[id] = {}
        for (let i = 1; i < d.length; i++) {
          k = header[i]
          const v = CSV_NUMBERS.includes(k) ? +d[i] : d[i]
          data[id][k] = v
        }
      }
    }).on('end', () => resolve())
  })
  return data
}

async function main(){
  const allExports = {
    pubmedArticles: await fromCsv('test/exports/dashboard_pubmedArticlesJson.csv'),
    pubmedAuthors: await fromCsv('test/exports/dashboard_pubmedAuthorsJson.csv'),
    youtubeAnnual: JSON.parse(await fs.readFile('test/exports/dashboard_youtubeAnnualJson.json'))['data'],
    ehden: JSON.parse(await fs.readFile('test/exports/ehdenJson.json'))['data'].reduce((acc, e) => ({...acc, ...e}), {}),
    pubmed: JSON.parse(await fs.readFile('test/exports/pubmedJson.json')),
    youtube: JSON.parse(await fs.readFile('test/exports/youtubeJson.json')),
  }
  await fs.writeFile('test/exports/all.json', JSON.stringify(allExports, undefined, 2))
}
main()