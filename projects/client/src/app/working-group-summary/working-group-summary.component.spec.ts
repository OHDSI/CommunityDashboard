import { ComponentFixture, TestBed } from '@angular/core/testing';

import { WorkingGroupSummaryComponent } from './working-group-summary.component';

describe('WorkingGroupSummaryComponent', () => {
  let component: WorkingGroupSummaryComponent;
  let fixture: ComponentFixture<WorkingGroupSummaryComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ WorkingGroupSummaryComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(WorkingGroupSummaryComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
