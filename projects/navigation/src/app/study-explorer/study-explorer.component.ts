import { Component, ComponentRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatInputModule } from '@angular/material/input';
import { map, Observable } from 'rxjs';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { MatStepperModule, StepperOrientation } from '@angular/material/stepper';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatButtonModule } from '@angular/material/button';
import { MatListModule } from '@angular/material/list';
import { StudiesTableComponent } from '../studies-table/studies-table.component';
import { MatGridListModule } from '@angular/material/grid-list';
import { StudyExplorerTabsComponent } from '../study-explorer-tabs/study-explorer-tabs.component';
import { CdkPortalOutletAttachedRef, ComponentPortal, PortalModule } from '@angular/cdk/portal';
import { StudyExplorerMetricsComponent } from '../study-explorer-metrics/study-explorer-metrics.component';

@Component({
  selector: 'app-study-explorer',
  standalone: true,
  imports: [
    StudiesTableComponent,
    MatGridListModule,
    MatStepperModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatListModule,
    PortalModule,
    FormsModule,
    ReactiveFormsModule,
    CommonModule
  ],
  templateUrl: './study-explorer.component.html',
  styleUrls: ['./study-explorer.component.css']
})
export class StudyExplorerComponent {

  studyExplorerTabs = new ComponentPortal(StudyExplorerTabsComponent)
  studyExplorerMetrics = new ComponentPortal(StudyExplorerMetricsComponent)

  layout = this.breakpointObserver.observe([Breakpoints.XSmall, Breakpoints.Small, Breakpoints.Medium]).pipe(
    map(({ breakpoints }) => {
      if (breakpoints[Breakpoints.XSmall]) {
        return {
          tiles: [
            { cols: 12, rows: 4, portal: this.studyExplorerMetrics, inputs: {} },
            { cols: 12, rows: 4, portal: this.studyExplorerTabs, inputs: {} },
          ]
        }
       } else if (breakpoints[Breakpoints.Small]) {
        return {
          tiles: [
            { cols: 6, rows: 4, portal: this.studyExplorerMetrics, inputs: {} },
            { cols: 6, rows: 4, portal: this.studyExplorerTabs, inputs: {} },
          ]
        }
     } else {
        return {
          tiles: [
            { cols: 4, rows: 4, portal: this.studyExplorerMetrics, inputs: {} },
            { cols: 8, rows: 4, portal: this.studyExplorerTabs, inputs: {} },
          ]
        }
      }
    })
  );

  unmodifiedFormGroup = this.formBuilder.group({
    unmodifiedControl: ['', Validators.required],
  });

  stepperOrientation: Observable<StepperOrientation> = this.breakpointObserver
    .observe([Breakpoints.XSmall, Breakpoints.Small])
    .pipe(map(({matches}) => (matches ? 'vertical' : 'horizontal')));

  constructor(
    private formBuilder: FormBuilder, 
    private breakpointObserver: BreakpointObserver,
  ) {}

  setInputs(ref: CdkPortalOutletAttachedRef, inputs: object) {
    ref = ref as ComponentRef<any>
    for (const [k, v] of Object.entries(inputs)) {
      ref.setInput(k, v)
    }
  }

}
