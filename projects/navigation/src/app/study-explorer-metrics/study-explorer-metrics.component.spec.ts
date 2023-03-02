import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StudyExplorerMetricsComponent } from './study-explorer-metrics.component';

describe('StudyExplorerMetricsComponent', () => {
  let component: StudyExplorerMetricsComponent;
  let fixture: ComponentFixture<StudyExplorerMetricsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ StudyExplorerMetricsComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(StudyExplorerMetricsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
