import { Ehden } from "./ehden.service";
import * as Plot from "@observablehq/plot";
import * as d3 from "d3";

export function renderPlot(e: Ehden, height?: number) {
  const usersAnnually = e.users.map(u => ({
    year: +u.year,
    number_of_users: +u.number_of_users,
  })).filter(u => u.year != 1970)
  return Plot.plot({
    height,
    x: {tickFormat: ""},
    marks: [
      Plot.barY(usersAnnually, {x: "year", y: "number_of_users", fill: "steelblue"})
    ]
  })
}