import * as Plot from "@observablehq/plot";
import * as d3 from 'd3';
import { PublicationSummary } from "./pubmed.service";

const PRIMARY = '#20425a'
const SECONDARY = '#ff9800'

export function renderPlot(ys: PublicationSummary[]) {
  // https://observablehq.com/@d3/bar-line-chart
  const height = 400
  const width = 640
  const margin = ({top: 20, right: 60, bottom: 30, left: 40})

  const x = d3.scaleBand()
    .domain(ys.map(d => d.year))
    .rangeRound([margin.left, width - margin.right])
    .padding(0.1)

  const y1 = d3.scaleLinear()
    .domain([0, d3.max(ys, (d: PublicationSummary) => d.n)])
    .rangeRound([height - margin.bottom, margin.top])

  const y2 = d3.scaleLinear()
    .domain(d3.extent(ys, (d: PublicationSummary) => d.cumulativeCitations))
    .rangeRound([height - margin.bottom, margin.top])

  const line = d3.line()
    .x((d: PublicationSummary) => x(d.year) + x.bandwidth() / 2)
    .y((d: PublicationSummary) => y2(d.cumulativeCitations))

  const xAxis = (g: any) => g
    .attr("transform", `translate(0,${height - margin.bottom})`)
    .call(d3.axisBottom(x)
        .tickValues(d3.ticks(...d3.extent(x.domain()), width / 40).filter((v: any) => x(v) !== undefined))
        .tickSizeOuter(0))

  const y1Axis = (g: any) => g
    .attr("transform", `translate(${margin.left},0)`)
    .style("color", "steelblue")
    .call(d3.axisLeft(y1).ticks(null, "s"))
    .call((g: any) => g.select(".domain").remove())
    .call((g: any) => g.append("text")
        .attr("x", -margin.left)
        .attr("y", 10)
        .attr("fill", "currentColor")
        .attr("text-anchor", "start")
        .text('Publications'))

  const y2Axis = (g: any) => g
    .attr("transform", `translate(${width - margin.right},0)`)
    .call(d3.axisRight(y2))
    .style("color", SECONDARY)
    .call((g: any) => g.select(".domain").remove())
    .call((g: any) => g.append("text")
        .attr("x", margin.right)
        .attr("y", 10)
        .attr("fill", "currentColor")
        .attr("text-anchor", "end")
        .text('Cumulative Citations'))

  const svg = d3.create("svg")
    .attr("viewBox", [0, 0, width, height])
    // .attr('style', 'height: 100%;')

  svg.append("g")
      .attr("fill", "steelblue")
      .attr("fill-opacity", 0.8)
    .selectAll("rect")
    .data(ys)
    .join("rect")
      .attr("x", (d: PublicationSummary) => x(d.year))
      .attr("width", x.bandwidth())
      .attr("y", (d: PublicationSummary) => y1(d.n))
      .attr("height", (d: PublicationSummary) => y1(0) - y1(d.n));

  svg.append("path")
      .style("color", SECONDARY)
      .attr("fill", "none")
      .attr("stroke", "currentColor")
      .attr("stroke-miterlimit", 1)
      .attr("stroke-width", 3)
      .attr("d", line(ys));

  svg.append("g")
      .attr("fill", "none")
      .attr("pointer-events", "all")
    .selectAll("rect")
    .data(ys)
    .join("rect")
      .attr("x", (d: PublicationSummary) => x(d.year))
      .attr("width", x.bandwidth())
      .attr("y", 0)
      .attr("height", height)
    .append("title")
      .text((d: PublicationSummary) => `${d.year}
${d.n.toLocaleString("en")} publications
${d.cumulativeCitations.toLocaleString("en")} total citations (cumulative)`);

  svg.append("g")
      .call(xAxis);

  svg.append("g")
      .call(y1Axis);

  svg.append("g")
      .call(y2Axis);

  return svg.node()
}