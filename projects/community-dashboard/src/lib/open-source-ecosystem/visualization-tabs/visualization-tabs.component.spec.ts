import { ComponentFixture, TestBed } from '@angular/core/testing';

import { VisualizationTabsComponent } from './visualization-tabs.component';

describe('VisualizationTabsComponent', () => {
  let component: VisualizationTabsComponent;
  let fixture: ComponentFixture<VisualizationTabsComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [VisualizationTabsComponent]
    });
    fixture = TestBed.createComponent(VisualizationTabsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
