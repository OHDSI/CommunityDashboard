import * as d3 from "d3"

const height = 400
const width = 640
const margin = {left: 40, bottom: 40, right: 20, top: 20}

const cadenceViolin = (data, xVar, yVar, bandwidth, buckets) => {

  const svg = d3.create('svg')
    .attr('height', height)
    .attr('width', width)
    .style('font-family', 'sans-serif')
    .style('font-size', 12)
  
  const x = d3.scaleBand()
    .domain(_.uniq(data.map(d => d[xVar])))
    .range([margin.left, width - margin.right])
    .padding(0.05)
  
  const y = d3.scaleLinear()
    .domain(d3.extent(data, d => d[yVar])).nice()
    .range([height - margin.bottom, margin.top])
  
  const xAxis = g => g
    .attr('transform', `translate(0, ${height - margin.bottom})`)
    .call(d3.axisBottom(x).tickSizeOuter(0))
  
  const yAxis = g => g
    .attr('transform', `translate(${margin.left}, 0)`)
    .call(d3.axisLeft(y))
    .call(g => g.select('.domain').remove())
  
  function kde(kernel, thds) {
    return V => thds.map(t => [t, d3.mean(V, d => kernel(t - d))])
  }
  
  function epanechnikov(bandwidth) {
    return x => Math.abs(x /= bandwidth) <= 1 ? 0.75 * (1 - x * x) / bandwidth : 0;
  }
  
  const thds = y.ticks(buckets)
  const density = kde(epanechnikov(bandwidth), thds)
  
  const violins = d3.rollup(data, v => density(v.map(g => g[yVar])), d => d[xVar])
  
  var allNum = [];
  [...violins.values()].forEach((d,i) => allNum = allNum.concat([...violins.values()][i].map(d => d[1])))
  const xNum  = d3.scaleLinear()
    .domain([-d3.max(allNum), d3.max(allNum)])
    .range([0, x.bandwidth()])
  
  const area = d3.area()
    .x0(d => xNum(-d[1]))
    .x1(d => xNum(d[1]))
    .y(d => y(d[0]))
    .curve(d3.curveStep)
  
  svg.append('g')
    .call(xAxis)
  
  svg.append('g')
    .call(yAxis)
  
  svg.append('g')
    .selectAll('g')
    .data([...violins])
    .join('g')
      .attr('transform', d => `translate(${x(d[0])}, 0)`)
    .append('path')
      .datum(d => d[1])
      .style('stroke', 'none')
      .style('fill', '#69b3a2')
      .attr('d', area)
  
  return svg.node()
}

export default cadenceViolin