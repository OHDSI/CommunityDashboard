import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { CdkPortalOutletAttachedRef, ComponentPortal, PortalModule } from '@angular/cdk/portal';
import { CommonModule } from '@angular/common';
import { Component, ComponentRef } from '@angular/core';
import { MatGridListModule } from '@angular/material/grid-list';
import { Observable } from 'rxjs';
import { map } from 'rxjs';
import { PhenotypeExplorerMetricsComponent } from './phenotype-explorer-metrics/phenotype-explorer-metrics.component';
import { PhenotypeExplorerTableComponentComponent } from './phenotype-explorer-table/phenotype-explorer-table.component';
import { PhenotypeExplorerTabsComponent } from './phenotype-explorer-tabs/phenotype-explorer-tabs.component';

@Component({
  selector: 'app-phenotype',
  standalone: true,
  templateUrl: './phenotype-explorer.component.html',
  styleUrls: ['./phenotype-explorer.component.css'],
  imports: [
    PhenotypeExplorerTableComponentComponent,
    MatGridListModule,
    PortalModule,
    CommonModule,
  ]
})
export class PhenotypeExplorerComponent {

  phenotypeExplorerTabsComponentComponent = new ComponentPortal(PhenotypeExplorerTabsComponent)
  phenotypeExplorerMetricsComponentComponent = new ComponentPortal(PhenotypeExplorerMetricsComponent)

  layout = this.breakpointObserver.observe([Breakpoints.XSmall, Breakpoints.Small, Breakpoints.Medium]).pipe(
    map(({ breakpoints }) => {
      if (breakpoints[Breakpoints.XSmall]) {
        return {
          tiles: [
            { cols: 12, rows: 3, portal: this.phenotypeExplorerMetricsComponentComponent, inputs: {} },
            { cols: 12, rows: 0, portal: this.phenotypeExplorerTabsComponentComponent, inputs: {} },
          ]
        }
       } else if (breakpoints[Breakpoints.Small]) {
        return {
          tiles: [
            { cols: 6, rows: 3, portal: this.phenotypeExplorerMetricsComponentComponent, inputs: {} },
            { cols: 6, rows: 0, portal: this.phenotypeExplorerTabsComponentComponent, inputs: {} },
          ]
        }
     } else {
        return {
          tiles: [
            { cols: 4, rows: 3, portal: this.phenotypeExplorerMetricsComponentComponent, inputs: {} },
            { cols: 8, rows: 0, portal: this.phenotypeExplorerTabsComponentComponent, inputs: {} },
          ]
        }
      }
    })
  );

  displayedColumns: Observable<string[]> = this.breakpointObserver.observe([Breakpoints.XSmall, Breakpoints.Small, Breakpoints.Medium]).pipe(
    map(({ breakpoints }) => {
      if (breakpoints[Breakpoints.XSmall]) {
        return ['cohortId', 'cohortName', 'modifiedDate']
       } else if (breakpoints[Breakpoints.Small]) {
        return ['cohortId', 'cohortName', 'modifiedDate']
      } else {
        return ['cohortId', 'cohortName', 'modifiedDate', 'status', 'hashTag']
      }
    })
  );

  constructor(
    private breakpointObserver: BreakpointObserver
  ) {}

  setInputs(ref: CdkPortalOutletAttachedRef, inputs: object) {
    ref = ref as ComponentRef<any>
    for (const [k, v] of Object.entries(inputs)) {
      ref.setInput(k, v)
    }
  }
}
