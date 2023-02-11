import { Component, ComponentRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatGridListModule } from '@angular/material/grid-list';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { map } from 'rxjs';
import { CdkPortalOutletAttachedRef, ComponentPortal, PortalModule } from '@angular/cdk/portal';
import { YouTubeWelcomeComponent } from '../you-tube-welcome/you-tube-welcome.component';
import { YouTubeTabsComponent } from '../you-tube-tabs/you-tube-tabs.component';
import { YouTubeTableComponent } from '../you-tube-table/you-tube-table.component';

@Component({
  selector: 'app-you-tube',
  standalone: true,
  imports: [
    YouTubeTableComponent,
    MatGridListModule,
    PortalModule,
    CommonModule
  ],
  templateUrl: './you-tube.component.html',
  styleUrls: ['./you-tube.component.css']
})
export class YouTubeComponent {

  youTubeWelcomePortal = new ComponentPortal(YouTubeWelcomeComponent)
  youTubeTabs = new ComponentPortal(YouTubeTabsComponent)

  layout = this.breakpointObserver.observe([Breakpoints.XSmall, Breakpoints.Small, Breakpoints.Medium]).pipe(
    map(({ breakpoints }) => {
      if (breakpoints[Breakpoints.XSmall]) {
        return {
          columns: ['Title', 'Date Published', 'Total Views'],
          tiles: [
            { cols: 12, rows: 4, portal: this.youTubeWelcomePortal, inputs: {} },
            { cols: 12, rows: 4, portal: this.youTubeTabs, inputs: {} },
          ]
        }
       } else if (breakpoints[Breakpoints.Small]) {
        return {
          columns: ['Title', 'Date Published', 'Total Views', 'Recent Views', 'SNOMED Terms (n)'],
          tiles: [
            { cols: 6, rows: 4, portal: this.youTubeWelcomePortal, inputs: {} },
            { cols: 6, rows: 4, portal: this.youTubeTabs, inputs: {} },
          ]
        }
     } else {
        return {
          columns: ['Title', 'Date Published', 'Length', 'Total Views', 'Recent Views', 'SNOMED Terms (n)'],
          tiles: [
            { cols: 4, rows: 4, portal: this.youTubeWelcomePortal, inputs: {} },
            { cols: 8, rows: 4, portal: this.youTubeTabs, inputs: {} },
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


