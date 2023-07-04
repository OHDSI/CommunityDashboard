import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ProjectDrilldownComponent } from './project-drilldown.component';

describe('ProjectDrilldownComponent', () => {
  let component: ProjectDrilldownComponent;
  let fixture: ComponentFixture<ProjectDrilldownComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [ProjectDrilldownComponent]
    });
    fixture = TestBed.createComponent(ProjectDrilldownComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
