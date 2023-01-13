import { Component, ComponentRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatGridListModule } from '@angular/material/grid-list';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { map } from 'rxjs';
import { WelcomeComponent } from '../dashboard-welcome/dashboard-welcome.component';
import { YouTubeSummaryComponent } from '../you-tube-summary/you-tube-summary.component';
import { EhdenSummaryComponent } from '../ehden-summary/ehden-summary.component';
import { WorkingGroupSummaryComponent } from '../working-group-summary/working-group-summary.component';
import { CdkPortalOutletAttachedRef, ComponentPortal, PortalModule } from '@angular/cdk/portal';
import { PubMedSummaryComponent } from '../pub-med-summary/pub-med-summary.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    MatGridListModule,
    PortalModule,
    CommonModule,
  ],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent {

  welcomePortal = new ComponentPortal(WelcomeComponent)
  youTubePortal = new ComponentPortal(YouTubeSummaryComponent)
  pubMedPortal = new ComponentPortal(PubMedSummaryComponent)
  ehdenPortal = new ComponentPortal(EhdenSummaryComponent)
  workingGroupPortal = new ComponentPortal(WorkingGroupSummaryComponent)

  layout = this.breakpointObserver.observe([Breakpoints.XSmall, Breakpoints.Small, Breakpoints.Medium]).pipe(
    map(({ breakpoints }) => {
      if (breakpoints[Breakpoints.XSmall]) {
        return [
          { cols: 12, rows: 4, portal: this.welcomePortal, inputs: {} },
          { cols: 12, rows: 4, portal: this.pubMedPortal, inputs: {orientation: 'vertical'} },
          { cols: 12, rows: 4, portal: this.youTubePortal, inputs: {orientation: 'vertical'}  },
          { cols: 12, rows: 4, portal: this.ehdenPortal, inputs: {orientation: 'vertical'}  },
          { cols: 12, rows: 2, portal: this.workingGroupPortal, inputs: {} },
        ]
       } else if (breakpoints[Breakpoints.Small]) {
        return [
          { cols: 6, rows: 5, portal: this.welcomePortal, inputs: {} },
          { cols: 6, rows: 3, portal: this.pubMedPortal, inputs: {orientation: 'vertical'} },
          { cols: 6, rows: 3, portal: this.youTubePortal, inputs: {orientation: 'vertical'} },
          { cols: 6, rows: 3, portal: this.ehdenPortal, inputs: {orientation: 'vertical'} },
          { cols: 6, rows: 2, portal: this.workingGroupPortal, inputs: {} },
        ]
     } else {
        return [
          { cols: 4, rows: 4, portal: this.welcomePortal, inputs: {} },
          { cols: 8, rows: 3, portal: this.pubMedPortal, inputs: {orientation: 'horizontal'} },
          { cols: 8, rows: 1, portal: this.workingGroupPortal, inputs: {orientation: 'horizontal'} },
          { cols: 6, rows: 3, portal: this.youTubePortal, inputs: {orientation: 'vertical'} },
          { cols: 6, rows: 3, portal: this.ehdenPortal, inputs: {orientation: 'vertical'} },
        ]
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
