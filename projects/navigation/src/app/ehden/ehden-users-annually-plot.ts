import { Ehden } from "./ehden.service";
import * as Plot from "@observablehq/plot";

export function renderPlot(e: Ehden, height?: number) {
  const usersAnnually = e.users.map(u => ({
    year: +u.year,
    number_of_users: +u.number_of_users,
  })).filter(u => u.year != 1970)
  return Plot.plot({
    height,
    marks: [
      Plot.barY(usersAnnually, {x: "year", y: "number_of_users", fill: "steelblue"})
    ]
  })
}