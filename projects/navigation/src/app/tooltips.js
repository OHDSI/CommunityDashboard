// https://stackoverflow.com/questions/71328696/adding-tooltip-functionality-to-observablehq-plot-locally
import {html} from 'htl'
import * as d3 from "d3"
import * as _ from 'lodash'

// const html = htl.html
  
  // function scatter(data) {
  //   const div = document.getElementById("chart1")
  //   div.appendChild(addTooltips(Plot.plot({
  //     marks: [
  //       Plot.dot(data, {x: "sepalLength", y: "sepalWidth", stroke: "species", 
  //           title: (d) =>
  //       `${d.species} \n Sepal Length: ${d.sepalLength} \n Sepal Width: ${d.sepalWidth}` 
  //       }),
  //     ],              
  //   })))
  // }
  
function addTooltips(chart, hover_styles = { fill: "blue", opacity: 0.5 }) {
  let styles = hover_styles;
  const line_styles = {
    stroke: "blue",
    "stroke-width": 3
  };
  // Workaround if it's in a figure
  const type = d3.select(chart).node().tagName;
  let wrapper =
    type === "FIGURE" ? d3.select(chart).select("svg") : d3.select(chart);

  // Workaround if there's a legend....
  const numSvgs = d3.select(chart).selectAll("svg").size();
  if (numSvgs === 2)
    wrapper = d3
      .select(chart)
      .selectAll("svg")
      .filter((d, i) => i === 1);
  wrapper.style("overflow", "visible"); // to avoid clipping at the edges

  // Set pointer events to visibleStroke if the fill is none (e.g., if its a line)
  wrapper.selectAll("path").each(function (data, index, nodes) {
    // For line charts, set the pointer events to be visible stroke
    if (
      d3.select(this).attr("fill") === null ||
      d3.select(this).attr("fill") === "none"
    ) {
      d3.select(this).style("pointer-events", "visibleStroke");
      styles = _.isEqual(hover_styles, { fill: "blue", opacity: 0.5 })
        ? line_styles
        : hover_styles;
    }
  });

  const tip = wrapper
    .selectAll(".hover-tip")
    .data([""])
    .join("g")
    .attr("class", "hover")
    .style("pointer-events", "none")
    .style("text-anchor", "middle");

  // Add a unique id to the chart for styling
  const id = id_generator();

  // Add the event listeners
  d3.select(chart)
    .classed(id, true) // using a class selector so that it doesn't overwrite the ID
    .selectAll("title")
    .each(function () {
      // Get the text out of the title, set it as an attribute on the parent, and remove it
      const title = d3.select(this); // title element that we want to remove
      const parent = d3.select(this.parentNode); // visual mark on the screen
      const t = title.text();
      if (t) {
        parent.attr("__title", t).classed("has-title", true);
        title.remove();
      }
      // Mouse events
      parent
        .on("mousemove", function (event) {
          const text = d3.select(this).attr("__title");
          const pointer = d3.pointer(event, wrapper.node());
          if (text) tip.call(hover, pointer, text.split("\n"));
          else tip.selectAll("*").remove();

          // Raise it
          d3.select(this).raise();
          // Keep within the parent horizontally
          const tipSize = tip.node().getBBox();
          if (pointer[0] + tipSize.x < 0)
            tip.attr(
              "transform",
              `translate(${tipSize.width / 2}, ${pointer[1] + 7})`
            );
          else if (pointer[0] + tipSize.width / 2 > wrapper.attr("width"))
            tip.attr(
              "transform",
              `translate(${wrapper.attr("width") - tipSize.width / 2}, ${
                pointer[1] + 7
              })`
            );
        })
        .on("mouseout", function (event) {
          tip.selectAll("*").remove();
          // Lower it!
          d3.select(this).lower();
        });
    });

  // Remove the tip if you tap on the wrapper (for mobile)
  wrapper.on("touchstart", () => tip.selectAll("*").remove());
  // Add styles
  const style_string = Object.keys(styles)
    .map((d) => {
      return `${d}:${styles[d]};`;
    })
    .join("");

  // Define the styles
  const style = html`<style>
      .${id} .has-title {
        cursor: pointer; 
        pointer-events: all;
      }
      .${id} .has-title:hover {
        ${style_string}
    }
    </style>`;
  chart.appendChild(style);
  return chart;
}

function hover(tip, pos, text){
  const side_padding = 10;
  const vertical_padding = 5;
  const vertical_offset = 15;

  // Empty it out
  tip.selectAll("*").remove();

  // Append the text
  tip
    .style("text-anchor", "middle")
    .style("pointer-events", "none")
    .attr("transform", `translate(${pos[0]}, ${pos[1] + 7})`)
    .selectAll("text")
    .data(text)
    .join("text")
    .style("dominant-baseline", "ideographic")
    .text((d) => d)
    .attr("y", (d, i) => (i - (text.length - 1)) * 15 - vertical_offset)
    .style("font-weight", (d, i) => (i === 0 ? "bold" : "normal"));

  const bbox = tip.node().getBBox();

  // Add a rectangle (as background)
  tip
    .append("rect")
    .attr("y", bbox.y - vertical_padding)
    .attr("x", bbox.x - side_padding)
    .attr("width", bbox.width + side_padding * 2)
    .attr("height", bbox.height + vertical_padding * 2)
    .style("fill", "white")
    .style("stroke", "#d3d3d3")
    .lower();
}
function id_generator(){
  var S4 = function () {
    return (((1 + Math.random()) * 0x10000) | 0).toString(16).substring(1);
  };
  return "a" + S4() + S4();
}
// scatter(iris)

export default addTooltips