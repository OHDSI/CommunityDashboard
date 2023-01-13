import { Component, ComponentRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatGridListModule } from '@angular/material/grid-list';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { map } from 'rxjs';
import { CdkPortalOutletAttachedRef, ComponentPortal, PortalModule } from '@angular/cdk/portal';
import { EhdenWelcomeComponent } from '../ehden-welcome/ehden-welcome.component';
import { EhdenTabsComponent } from '../ehden-tabs/ehden-tabs.component';
import { EhdenTableComponent } from '../ehden-table/ehden-table.component';

@Component({
  selector: 'app-ehden',
  standalone: true,
  imports: [
    EhdenTableComponent,
    MatGridListModule,
    PortalModule,
    CommonModule
  ],
  templateUrl: './ehden.component.html',
  styleUrls: ['./ehden.component.css']
})
export class EhdenComponent {

  ehdenWelcomePortal = new ComponentPortal(EhdenWelcomeComponent)
  ehdenTabs = new ComponentPortal(EhdenTabsComponent)

  layout = this.breakpointObserver.observe([Breakpoints.XSmall, Breakpoints.Small, Breakpoints.Medium]).pipe(
    map(({ breakpoints }) => {
      if (breakpoints[Breakpoints.XSmall]) {
        return {
          columns: ['course_fullname', 'started', 'completions'],
          tiles: [
            { cols: 12, rows: 4, portal: this.ehdenWelcomePortal, inputs: {} },
            { cols: 12, rows: 4, portal: this.ehdenTabs, inputs: {} },
          ]
        }
       } else if (breakpoints[Breakpoints.Small]) {
        return {
          columns: ['course_fullname', 'started', 'completions', 'course_started'],
          tiles: [
            { cols: 6, rows: 4, portal: this.ehdenWelcomePortal, inputs: {} },
            { cols: 6, rows: 4, portal: this.ehdenTabs, inputs: {} },
          ]
        }
     } else {
        return {
          columns: ['course_fullname', 'course_shortname', 'category', 'started', 'completions', 'course_started'],
          tiles: [
            { cols: 4, rows: 4, portal: this.ehdenWelcomePortal, inputs: {} },
            { cols: 8, rows: 4, portal: this.ehdenTabs, inputs: {} },
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

