import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StudyExplorerTabsComponent } from './study-explorer-tabs.component';

describe('StudyExplorerTabsComponent', () => {
  let component: StudyExplorerTabsComponent;
  let fixture: ComponentFixture<StudyExplorerTabsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ StudyExplorerTabsComponent ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(StudyExplorerTabsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
