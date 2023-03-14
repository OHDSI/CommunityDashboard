import { Component, ComponentRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatGridListModule } from '@angular/material/grid-list';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { map } from 'rxjs';
import { CdkPortalOutletAttachedRef, ComponentPortal, PortalModule } from '@angular/cdk/portal';
import { PubMedWelcomeComponent } from '../pub-med-welcome/pub-med-welcome.component';
import { PubMedTabsComponent } from '../pub-med-tabs/pub-med-tabs.component';
import { PubMedTableComponent } from '../pub-med-table/pub-med-table.component';

@Component({
  selector: 'app-pub-med',
  standalone: true,
  imports: [
    PubMedTableComponent,
    MatGridListModule,
    PortalModule,
    CommonModule
  ],
  templateUrl: './pub-med.component.html',
  styleUrls: ['./pub-med.component.css']
})
export class PubMedComponent {

  pubMedWelcomePortal = new ComponentPortal(PubMedWelcomeComponent)
  pubMedTabs = new ComponentPortal(PubMedTabsComponent)

  layout = this.breakpointObserver.observe([Breakpoints.XSmall, Breakpoints.Small, Breakpoints.Medium]).pipe(
    map(({ breakpoints }) => {
      if (breakpoints[Breakpoints.XSmall]) {
        return {
          columns: ['creationDate', 'fullAuthorEdited', 'title'],
          tiles: [
            { cols: 12, rows: 4, portal: this.pubMedWelcomePortal, inputs: {} },
            { cols: 12, rows: 4, portal: this.pubMedTabs, inputs: {} },
          ]
        }
       } else if (breakpoints[Breakpoints.Small]) {
        return {
          columns: ['creationDate', 'fullAuthorEdited', 'title', 'termFreq'],
          tiles: [
            { cols: 6, rows: 4, portal: this.pubMedWelcomePortal, inputs: {} },
            { cols: 6, rows: 4, portal: this.pubMedTabs, inputs: {} },
          ]
        }
     } else {
        return {
          columns: ['pubmedID', 'creationDate', 'fullAuthorEdited', 'title', 'journalTitle', 'termFreq', 'numCitations'],
          tiles: [
            { cols: 4, rows: 4, portal: this.pubMedWelcomePortal, inputs: {} },
            { cols: 8, rows: 4, portal: this.pubMedTabs, inputs: {} },
          ]
        }
      }
    })
  );

  constructor(
    private breakpointObserver: BreakpointObserver,
  ) {}

  setInputs(ref: CdkPortalOutletAttachedRef, inputs: object) {
    ref = ref as ComponentRef<any>
    for (const [k, v] of Object.entries(inputs)) {
      ref.setInput(k, v)
    }
  }
}
