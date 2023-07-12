import { Component, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatStepper, MatStepperModule } from '@angular/material/stepper';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { ViewChild } from '@angular/core';

@Component({
  selector: 'lib-network-study-checklist',
  standalone: true,
  imports: [    
    MatStepperModule,
    MatListModule,
    MatIconModule,
    MatFormFieldModule,
    ReactiveFormsModule,
    CommonModule
  ],
  templateUrl: './network-study-checklist.component.html',
  styleUrls: ['./network-study-checklist.component.css']
})
export class NetworkStudyChecklistComponent implements AfterViewInit {
  @ViewChild(MatStepper) stepper!: MatStepper

  onboardingFormGroup = new FormGroup({})
  vocabularyCompletedControl = new FormControl(false, Validators.requiredTrue)
  vocabularyFormGroup = new FormGroup({
    vocabularyCompleted: this.vocabularyCompletedControl
  })
  diagnosticsFormGroup = new FormGroup({})

  ngAfterViewInit(): void {
    // this.onboardingFormGroup.markAsTouched()
    setTimeout(() => {
      this.stepper.selectedIndex = 1
    })
  }
}
