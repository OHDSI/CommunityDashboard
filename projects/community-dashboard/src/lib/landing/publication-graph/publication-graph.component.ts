import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import * as d3 from 'd3'
import { AfterViewInit } from '@angular/core';
import { ViewChild } from '@angular/core';
import { ElementRef } from '@angular/core';
import { from, map } from 'rxjs';

@Component({
  selector: 'lib-publication-graph',
  standalone: true,
  imports: [
    CommonModule
  ],
  templateUrl: './publication-graph.component.html',
  styleUrls: ['./publication-graph.component.css']
})
export class PublicationGraphComponent implements AfterViewInit {
  @ViewChild('svg', {read: ElementRef}) svg?: ElementRef

  ngAfterViewInit(): void {
    const el = this.svg!.nativeElement as HTMLElement
    const width = +el.getAttribute("width")!
    const height = +el.getAttribute("height")!
    const color = d3.scaleOrdinal(d3.schemeCategory10);
    const simulation = d3.forceSimulation()
      .force("link", d3.forceLink().id(function(d: any) { return d.id; }))
      .force("charge", d3.forceManyBody().strength(-175))
      .force("center", d3.forceCenter(width - (width/5), height / 2))
      // .force('edge', d3.forceY(-10))
      // .force('edge', d3.forceX(1000))

    function dragstarted(event: any, d: any) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event: any, d: any) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event: any, d: any) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }

    from(d3.json('/assets/graph.json')).pipe(
      map((graph: any) => {
        const svg = d3.create("svg")
          .attr("viewBox", [0, 0, width, height])
        var link = svg.append("g")
          .attr("class", "links")
        .selectAll("line")
        .data(graph.links)
        .enter().append("line")
          .attr("stroke-width", function(d: any) { return Math.sqrt(d.value); })
        .style("opacity", function(d: any) { return 0.8-0.6/Math.sqrt(d.value); });

        var node = svg.selectAll(".node")
          .data(graph.nodes)
          .enter().append("g")
          .attr("class", "node")
          .call(d3.drag()
              .on("start", dragstarted)
              .on("drag", dragged)
              .on("end", dragended));

        node.append("circle")
          .attr("r", function(d: any) { return 1+Math.sqrt(d.size); })
          .style("fill", function(d: any) { return d.color; })
          .style("opacity", 0.5)

        node.append("text")
          .attr("dx", 10)
          .attr("dy", ".35em")
          .text(function(d: any) { return d.id });  
            

        simulation
            .nodes(graph.nodes)
            .on("tick", ticked);

        simulation.force("link")
            .links(graph.links);

        function ticked() {
          link
              .attr("x1", function(d: any) { return d.source.x; })
              .attr("y1", function(d: any) { return d.source.y; })
              .attr("x2", function(d: any) { return d.target.x; })
              .attr("y2", function(d: any) { return d.target.y; });

            d3.selectAll("circle").attr("cx", function (d: any) {
              return d.x;
          })
              .attr("cy", function (d: any) {
              return d.y;
          });

          d3.selectAll("text").attr("x", function (d: any) {
              return d.x;
          })
              .attr("y", function (d: any) {
              return d.y;
          });
          
        
        }

        el.replaceChildren(svg.node())
      })
    ).subscribe()
  }

}

